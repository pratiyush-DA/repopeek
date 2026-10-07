"""Enrichment pipeline orchestrating bottom-up story generation over a CanonicalGraph."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from repopeek.enrichment.cache import StoryCache
from repopeek.enrichment.governor import CostGovernor
from repopeek.enrichment.summarizer import HierarchicalStoryGenerator
from repopeek.enrichment.verifier import FactVerifier
from repopeek.llm.base import LLMProvider
from repopeek.llm.factory import get_llm_provider
from repopeek.models.schema import CanonicalGraph, NodeCard, NodeStory


@dataclass
class EnrichmentReport:
    """Diagnostic audit report summarizing the outcome of graph enrichment."""
    total_nodes: int = 0
    stories_generated: int = 0
    cached_hits: int = 0
    deterministic_stories: int = 0
    llm_stories: int = 0
    governor_summary: Dict[str, Any] = field(default_factory=dict)


class StoryPipeline:
    """Topological enrichment orchestrator generating verifiable stories for graph nodes."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        cache_dir: Optional[Path] = None,
        max_tokens: int = 100_000,
        max_cost_usd: float = 1.00,
        dry_run: bool = False,
    ) -> None:
        self.provider = provider or get_llm_provider()
        cache_file = (cache_dir / "story_cache.json") if cache_dir else None
        self.cache = StoryCache(cache_file=cache_file)
        self.governor = CostGovernor(
            max_tokens=max_tokens,
            max_cost_usd=max_cost_usd,
            dry_run=dry_run,
        )
        self.verifier = FactVerifier()
        self.generator = HierarchicalStoryGenerator(
            provider=self.provider,
            cache=self.cache,
            governor=self.governor,
            verifier=self.verifier,
        )
        self.llm_allowlist: Optional[Set[str]] = None

    def enrich(self, graph: CanonicalGraph) -> EnrichmentReport:
        """Enrich all nodes in CanonicalGraph in bottom-up hierarchical order."""
        report = EnrichmentReport(total_nodes=len(graph.nodes))

        # 1. Partition nodes into levels for bottom-up execution
        methods_and_funcs: List[NodeCard] = []
        classes: List[NodeCard] = []
        modules: List[NodeCard] = []
        others: List[NodeCard] = []

        for node in graph.nodes.values():
            k = node.kind.lower()
            if k in ("function", "method"):
                methods_and_funcs.append(node)
            elif k == "class":
                classes.append(node)
            elif k in ("module", "file"):
                modules.append(node)
            else:
                others.append(node)

        total_items = len(methods_and_funcs) + len(classes) + len(modules) + len(others)
        done = 0
        llm_cap = max(0, int(os.environ.get("REPOPEEK_LLM_MAX_NODES", "200")))
        ranked_llm = sorted(
            [n for n in methods_and_funcs + classes if not HierarchicalStoryGenerator.is_trivial_node(n)],
            key=lambda n: (n.facts.complexity, n.facts.calls),
            reverse=True,
        )
        self.llm_allowlist = {n.id for n in ranked_llm[:llm_cap]}
        self.generator.llm_allowlist = self.llm_allowlist

        def _assign(nodes: List[NodeCard], with_children: bool = False) -> None:
            nonlocal done
            ordered = sorted(nodes, key=lambda n: n.id)
            workers = max(1, int(os.environ.get("REPOPEEK_LLM_CONCURRENCY", "2")))

            def _one(node: NodeCard) -> NodeStory:
                if with_children:
                    prefix = f"{node.id}."
                    child_stories = [
                        m.story for m in methods_and_funcs
                        if m.id.startswith(prefix) and m.story is not None
                    ]
                    return self.generator.generate_story(node, child_stories=child_stories)
                if node.kind.lower() in ("module", "file"):
                    fpath = node.span.file if node.span and node.span.file else ""
                    child_stories = [
                        n.story for n in (methods_and_funcs + classes)
                        if n.span and n.span.file == fpath and n.story is not None
                    ]
                    return self.generator.generate_story(node, child_stories=child_stories)
                return self.generator.generate_story(node)

            if workers == 1 or len(ordered) <= 1:
                for node in ordered:
                    node.story = _one(node)
                    self._tally_report(node.story, report)
                    done += 1
                    if done % 25 == 0 or done == total_items:
                        print(
                            f"  Enriched {done}/{total_items} nodes "
                            f"({report.llm_stories} LLM, {report.deterministic_stories} deterministic, {report.cached_hits} cached)...",
                            flush=True,
                        )
                return

            results: Dict[str, NodeStory] = {}
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = {pool.submit(_one, node): node.id for node in ordered}
                for fut in as_completed(futs):
                    nid = futs[fut]
                    story = fut.result()
                    results[nid] = story
                    self._tally_report(story, report)
                    done += 1
                    if done % 25 == 0 or done == total_items:
                        print(
                            f"  Enriched {done}/{total_items} nodes "
                            f"({report.llm_stories} LLM, {report.deterministic_stories} deterministic, {report.cached_hits} cached)...",
                            flush=True,
                        )
            for node in ordered:
                node.story = results[node.id]

        _assign(methods_and_funcs)
        _assign(classes, with_children=True)
        _assign(modules)
        _assign(others)

        # Save cache state to disk if path configured
        self.cache.save()
        report.governor_summary = self.governor.get_summary()

        return report

    @staticmethod
    def _tally_report(story: NodeStory, report: EnrichmentReport) -> None:
        """Increment diagnostic counter based on story generation source."""
        report.stories_generated += 1
        if story.source == "cached":
            report.cached_hits += 1
        elif story.source == "llm":
            report.llm_stories += 1
        else:
            report.deterministic_stories += 1
