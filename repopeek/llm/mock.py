"""Mock LLM provider adapter for offline deterministic unit testing."""

import json
from typing import Dict, List, Optional

from repopeek.llm.base import LLMProvider
from repopeek.llm.models import (
    CompletionRequest,
    CompletionResponse,
    LLMAuthenticationError,
    LLMProviderError,
    LLMRateLimitError,
    ModelTier,
    ProviderCapabilities,
)


class MockProvider(LLMProvider):
    """In-memory mock provider with history tracking and configurable error injection."""

    def __init__(
        self,
        canned_response: Optional[str] = None,
        canned_responses: Optional[Dict[str, str]] = None,
        simulate_rate_limit: bool = False,
        simulate_auth_error: bool = False,
        simulate_server_error: bool = False,
    ) -> None:
        self.canned_response = canned_response
        self.canned_responses = canned_responses or {}
        self.simulate_rate_limit = simulate_rate_limit
        self.simulate_auth_error = simulate_auth_error
        self.simulate_server_error = simulate_server_error
        self.history: List[CompletionRequest] = []

    def model_for_tier(self, tier: ModelTier) -> str:
        return f"mock-{tier.value}-model"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_structured_outputs=True,
            supports_json_mode=True,
            supports_prompt_caching=True,
            supports_batch_api=False,
            available_models=["mock-fast-model", "mock-balanced-model", "mock-strong-model"],
        )

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.history.append(request)

        if self.simulate_auth_error:
            raise LLMAuthenticationError("Simulated authentication error.")
        if self.simulate_rate_limit:
            raise LLMRateLimitError("Simulated rate limit (429).")
        if self.simulate_server_error:
            raise LLMProviderError("Simulated 500 internal server error.")

        # Determine response text
        if request.node_id and request.node_id in self.canned_responses:
            content = self.canned_responses[request.node_id]
        elif self.canned_response is not None:
            content = self.canned_response
        else:
            # Deterministic default JSON
            target = request.node_id or "node"
            content = json.dumps({"summary": f"Deterministic story summary for {target}"})

        return CompletionResponse(
            content=content,
            model=self.model_for_tier(request.tier),
            prompt_tokens=len(request.prompt.split()),
            completion_tokens=len(content.split()),
            total_tokens=len(request.prompt.split()) + len(content.split()),
            cached_tokens=0,
            latency_ms=1.5,
        )
