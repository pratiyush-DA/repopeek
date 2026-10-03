"""LLM provider abstraction layer for RepoPeek."""

from repopeek.llm.base import LLMProvider
from repopeek.llm.env import load_env_file
from repopeek.llm.fallback import DeterministicFallbackProvider
from repopeek.llm.factory import get_llm_provider
from repopeek.llm.groq import GroqProvider
from repopeek.llm.mock import MockProvider
from repopeek.llm.models import (
    CompletionRequest,
    CompletionResponse,
    LLMAuthenticationError,
    LLMModelNotFoundError,
    LLMProviderError,
    LLMRateLimitError,
    ModelTier,
    ProviderCapabilities,
)

__all__ = [
    "CompletionRequest",
    "CompletionResponse",
    "ModelTier",
    "ProviderCapabilities",
    "LLMProvider",
    "LLMProviderError",
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMModelNotFoundError",
    "GroqProvider",
    "MockProvider",
    "DeterministicFallbackProvider",
    "get_llm_provider",
    "load_env_file",
]
