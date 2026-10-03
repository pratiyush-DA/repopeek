"""Factory for resolving and instantiating configured LLM provider adapters."""

import os
from typing import Any, Optional

from repopeek.llm.base import LLMProvider
from repopeek.llm.env import load_env_file
from repopeek.llm.fallback import DeterministicFallbackProvider
from repopeek.llm.groq import GroqProvider
from repopeek.llm.mock import MockProvider


def get_llm_provider(provider_name: Optional[str] = None, **kwargs: Any) -> LLMProvider:
    """Return an instantiated LLMProvider based on configuration or environment state."""
    load_env_file()

    chosen = (
        provider_name
        or os.environ.get("REPOPEEK_LLM_PROVIDER")
        or ("groq" if os.environ.get("GROQ_API_KEY") else "fallback")
    ).lower()

    if chosen == "groq":
        return GroqProvider(**kwargs)
    elif chosen == "mock":
        return MockProvider(**kwargs)
    elif chosen in ("fallback", "deterministic", "offline"):
        return DeterministicFallbackProvider()
    else:
        raise ValueError(
            f"Unknown LLM provider '{chosen}'. Supported options: 'groq', 'mock', 'fallback'."
        )
