"""Abstract base class and contract for pluggable LLM provider adapters."""

from abc import ABC, abstractmethod
import json
import re
from typing import Any, Dict, Optional

from repopeek.llm.models import (
    CompletionRequest,
    CompletionResponse,
    ModelTier,
    ProviderCapabilities,
)


class LLMProvider(ABC):
    """Abstract interface decoupling code summarization and enrichment from specific LLM vendors."""

    @abstractmethod
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute a completion request and return normalized response."""
        pass

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Return feature capabilities and supported models of the adapter."""
        pass

    @abstractmethod
    def model_for_tier(self, tier: ModelTier) -> str:
        """Resolve an abstract model tier (fast, balanced, strong) to a concrete model identifier."""
        pass

    @staticmethod
    def extract_json(content: str) -> Optional[Dict[str, Any]]:
        """Safely extract and parse JSON object from raw response text or markdown code fence."""
        text = content.strip()
        if not text:
            return None

        # Try direct parse
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown ```json ... ``` fence
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            try:
                parsed = json.loads(match.group(1).strip())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        # Try extracting first {...} block
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace > first_brace:
            try:
                parsed = json.loads(text[first_brace : last_brace + 1])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        return None
