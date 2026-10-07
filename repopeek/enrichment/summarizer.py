"""Hierarchical story generator enforcing the 5-tier cost cascade and verifier."""

import json
from typing import Any, Dict, List, Optional

from repopeek.enrichment.cache import StoryCache
from repopeek.enrichment.governor import CostGovernor
from repopeek.enrichment.templates import DeterministicStoryBuilder
from repopeek.enrichment.verifier import FactVerifier
from repopeek.llm.base import LLMProvider
from repopeek.llm.fallback import DeterministicFallbackProvider
from repopeek.llm.models import CompletionRequest, ModelTier
from repopeek.models.schema import NodeCard, NodeStory


class HierarchicalStoryGenerator:
    """Orchestrates story generation through deterministic templates, caching, and tiered LLMs."""

    SYSTEM_PROMPT = (
        "You are an expert code intelligence engine. Given code symbols and AST facts, "
        "produce a single concise sentence (under 30 words) explaining the primary functional purpose. "
        "Do NOT invent unverified behaviors or external calls. Return ONLY valid JSON: {\"summary\": \"...\"}."
    )

    def __init__(
        self,
        provider: LLMProvider,
        cache: Optional[StoryCache] = None,
        governor: Optional[CostGovernor] = None,
        verifier: Optional[FactVerifier] = None,
    ) -> None:
        self.provider = provider
        self.cache = cache or StoryCache()
        self.governor = governor or CostGovernor()
        self.verifier = verifier or FactVerifier()
        self.llm_allowlist: Optional[set] = None

    @staticmethod
    def is_trivial_node(node: NodeCard) -> bool:
        """Identify trivial getters/setters/constants that should never invoke an LLM."""
        # Simple boilerplate functions with low complexity and zero external calls/reads/writes
        if node.kind in ("function", "method"):
            if (
                node.facts.complexity == 1
                and node.facts.calls == 0
                and not node.facts.reads
                and not node.facts.writes
            ):
                return True
        # Plain tables and configurations
        if node.kind in (
            "json_config",
            "yaml_config",
            "file",
            "external_symbol",
            "variable",
            "command",
            "sql_table",
        ):
            return True
        return False

    def generate_story(
        self,
        node: NodeCard,
        child_stories: Optional[List[NodeStory]] = None,
    ) -> NodeStory:
        """Produce an accurate story enforcing the 5-tier cost cascade."""
        # --- Tier 1: Trivial Code Filter ---
        if self.is_trivial_node(node):
            self.governor.record_fallback()
            return DeterministicStoryBuilder.build_story(node)

        # --- Tier 2: Content-Hash Cache ---
        cache_key = self.cache.make_key(node.content_hash, model_tier="fast")
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        allowlist = self.llm_allowlist
        if allowlist is not None and node.id not in allowlist:
            self.governor.record_fallback()
            story = DeterministicStoryBuilder.build_story(node)
            self.cache.put(cache_key, story)
            return story

        # --- Budget & Capability Pre-check ---
        if isinstance(self.provider, DeterministicFallbackProvider) or not self.governor.can_call_llm(estimated_tokens=150):
            self.governor.record_fallback()
            story = DeterministicStoryBuilder.build_story(node)
            self.cache.put(cache_key, story)
            return story

        # --- Tier 3 & 4: LLM Inference (Hierarchical Map-Reduce) ---
        user_prompt = self._build_prompt(node, child_stories)
        tier = ModelTier.STRONG if (node.facts.complexity >= 10) else ModelTier.FAST

        req = CompletionRequest(
            prompt=user_prompt,
            system=self.SYSTEM_PROMPT,
            tier=tier,
            temperature=0.1,
            max_tokens=80,
            response_format={"type": "json_object"},
            node_id=node.id,
        )

        try:
            resp = self.provider.complete(req)
            self.governor.record_usage(
                prompt_tokens=resp.prompt_tokens,
                completion_tokens=resp.completion_tokens,
                cached_tokens=resp.cached_tokens,
                model=resp.model,
            )

            # Extract narrative text
            parsed = self.provider.extract_json(resp.content)
            candidate_text = parsed.get("summary") if parsed else resp.content.strip()

            # --- Anti-Hallucination Fact Verifier ---
            v_res = self.verifier.verify(node, candidate_text)
            if v_res.is_valid:
                story = NodeStory(
                    text=candidate_text,
                    source="llm",
                    confidence=v_res.confidence,
                )
            else:
                # Downgrade to deterministic fallback if verifier rejects
                story = DeterministicStoryBuilder.build_story(node)
                story.confidence = "medium"

        except Exception:
            # Resilient fallback on any LLM or network failure
            self.governor.record_fallback()
            story = DeterministicStoryBuilder.build_story(node)

        self.cache.put(cache_key, story)
        return story

    def _build_prompt(self, node: NodeCard, child_stories: Optional[List[NodeStory]]) -> str:
        """Compose a concise prompt minimizing input tokens."""
        lines = [f"Node: {node.id}", f"Kind: {node.kind}"]
        if node.sig:
            lines.append(f"Signature: {node.sig}")
        if node.facts.params:
            lines.append(f"Parameters: {', '.join(node.facts.params)}")
        if node.facts.returns:
            lines.append(f"Returns: {node.facts.returns}")
        if node.facts.reads:
            lines.append(f"Reads: {', '.join(node.facts.reads[:3])}")
        if node.facts.writes:
            lines.append(f"Writes: {', '.join(node.facts.writes[:3])}")

        # Tier 4: Include child stories for compound nodes (classes/modules)
        if child_stories:
            lines.append("Child components:")
            for cs in child_stories[:5]:
                lines.append(f" - {cs.text}")

        return "\n".join(lines)
