"""Enrichment pipeline orchestrating bottom-up story generation over a CanonicalGraph."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

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

        # 2. Process functions and methods first
        for node in methods_and_funcs:
            story = self.generator.generate_story(node)
            node.story = story
            self._tally_report(story, report)
            done += 1
            if done % 100 == 0:
                print(f"  Enriched {done}/{total_items} nodes ({report.llm_stories} LLM, {report.deterministic_stories} deterministic, {report.cached_hits} cached)...")

        # 3. Process classes with child method stories
        for node in classes:
            # Find child methods defined within this class
            prefix = f"{node.id}."
            child_stories = [
                m.story for m in methods_and_funcs
                if m.id.startswith(prefix) and m.story is not None
            ]
            story = self.generator.generate_story(node, child_stories=child_stories)
            node.story = story
            self._tally_report(story, report)
            done += 1
            if done % 100 == 0:
                print(f"  Enriched {done}/{total_items} nodes ({report.llm_stories} LLM, {report.deterministic_stories} deterministic, {report.cached_hits} cached)...")

        # 4. Process modules with child class & function stories
        for node in modules:
            fpath = node.span.file if node.span and node.span.file else ""
            child_stories = [
                n.story for n in (methods_and_funcs + classes)
                if n.span and n.span.file == fpath and n.story is not None
            ]
            story = self.generator.generate_story(node, child_stories=child_stories)
            node.story = story
            self._tally_report(story, report)
            done += 1
            if done % 100 == 0:
                print(f"  Enriched {done}/{total_items} nodes ({report.llm_stories} LLM, {report.deterministic_stories} deterministic, {report.cached_hits} cached)...")

        # 5. Process remaining nodes (tables, queries, configs, scripts)
        for node in others:
            story = self.generator.generate_story(node)
            node.story = story
            self._tally_report(story, report)
            done += 1
            if done % 100 == 0:
                print(f"  Enriched {done}/{total_items} nodes ({report.llm_stories} LLM, {report.deterministic_stories} deterministic, {report.cached_hits} cached)...")

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
