"""Data models and exception classes for LLM provider abstraction."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModelTier(str, Enum):
    """Abstract model tiers decoupling application logic from concrete model identifiers."""
    FAST = "fast"
    BALANCED = "balanced"
    STRONG = "strong"


class CompletionRequest(BaseModel):
    """Unified completion request payload passed to LLM providers."""
    prompt: str = Field(description="User prompt or task input")
    system: Optional[str] = Field(default=None, description="System instructions / prompt prefix")
    tier: ModelTier = Field(default=ModelTier.FAST, description="Target model tier")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=200, ge=1, description="Maximum completion tokens")
    response_format: Optional[Dict[str, Any]] = Field(
        default=None, description="Schema definition or {'type': 'json_object'}"
    )
    node_id: Optional[str] = Field(default=None, description="Contextual target node identifier")


class CompletionResponse(BaseModel):
    """Normalized response returned by all LLM provider adapters."""
    content: str = Field(description="Raw generated response string")
    model: str = Field(description="Concrete model identifier that served the inference")
    prompt_tokens: int = Field(default=0, description="Input tokens processed")
    completion_tokens: int = Field(default=0, description="Output tokens generated")
    total_tokens: int = Field(default=0, description="Combined token volume")
    cached_tokens: int = Field(default=0, description="Input tokens served from prefix cache")
    latency_ms: float = Field(default=0.0, description="Roundtrip inference latency in milliseconds")


class ProviderCapabilities(BaseModel):
    """Feature matrix exposed by an LLM provider adapter."""
    supports_structured_outputs: bool = Field(default=True)
    supports_json_mode: bool = Field(default=True)
    supports_prompt_caching: bool = Field(default=True)
    supports_batch_api: bool = Field(default=False)
    available_models: List[str] = Field(default_factory=list)


class LLMProviderError(Exception):
    """Base error for LLM provider failures."""
    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when authentication credentials or API keys are missing or invalid."""
    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when request is throttled due to concurrency or rate limits (HTTP 429)."""
    pass


class LLMModelNotFoundError(LLMProviderError):
    """Raised when the specified model cannot be found or is inaccessible."""
    pass
