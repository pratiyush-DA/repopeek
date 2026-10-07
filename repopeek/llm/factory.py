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

    if provider_name:
        chosen = provider_name.lower()
    elif os.environ.get("REPOPEEK_OFFLINE", "").strip() in ("1", "true", "True", "yes"):
        chosen = "fallback"
    else:
        from repopeek.llm.groq import collect_groq_api_keys

        chosen = (
            os.environ.get("REPOPEEK_LLM_PROVIDER")
            or ("groq" if collect_groq_api_keys() else "fallback")
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
