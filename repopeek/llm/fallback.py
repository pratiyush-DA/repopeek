"""Deterministic rule-based fallback provider requiring zero network and zero API keys."""

import json
from typing import Optional

from repopeek.llm.base import LLMProvider
from repopeek.llm.models import (
    CompletionRequest,
    CompletionResponse,
    ModelTier,
    ProviderCapabilities,
)


class DeterministicFallbackProvider(LLMProvider):
    """Rule-based provider generating deterministic syntactic summaries from AST metadata."""

    def model_for_tier(self, tier: ModelTier) -> str:
        return "deterministic-ast-v1"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_structured_outputs=True,
            supports_json_mode=True,
            supports_prompt_caching=False,
            supports_batch_api=False,
            available_models=["deterministic-ast-v1"],
        )

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Generate a concise narrative without any external network calls."""
        node_id = request.node_id or "unnamed_node"
        lang = node_id.split(":", 1)[0] if ":" in node_id else "code"
        sym = node_id.split("::")[-1] if "::" in node_id else node_id

        summary = f"Syntactic definition of {lang} symbol '{sym}'"
        content = json.dumps({"summary": summary, "source": "deterministic"})

        return CompletionResponse(
            content=content,
            model="deterministic-ast-v1",
            prompt_tokens=0,
            completion_tokens=len(content.split()),
            total_tokens=len(content.split()),
            cached_tokens=0,
            latency_ms=0.1,
        )
