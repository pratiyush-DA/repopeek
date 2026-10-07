"""Tests for LLM provider abstraction, Groq adapter, mock provider, and JSON extractor."""

import json
import os
from pathlib import Path
import pytest

from repopeek.llm import (
    CompletionRequest,
    CompletionResponse,
    DeterministicFallbackProvider,
    GroqProvider,
    LLMAuthenticationError,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    MockProvider,
    ModelTier,
    get_llm_provider,
    load_env_file,
)


def test_mock_provider_basic():
    """Verify MockProvider records requests and returns expected completion."""
    provider = MockProvider()
    req = CompletionRequest(
        prompt="Explain function calc.add",
        tier=ModelTier.FAST,
        node_id="python:calc.py::add",
    )
    resp = provider.complete(req)

    assert resp.model == "mock-fast-model"
    assert resp.total_tokens > 0
    assert len(provider.history) == 1
    assert provider.history[0].node_id == "python:calc.py::add"

    parsed = LLMProvider.extract_json(resp.content)
    assert parsed is not None
    assert "summary" in parsed


def test_mock_provider_canned_responses():
    """Verify MockProvider respects custom canned responses mapped by node_id."""
    canned = {
        "node_1": json.dumps({"story": "Custom story 1"}),
        "node_2": json.dumps({"story": "Custom story 2"}),
    }
    provider = MockProvider(canned_responses=canned)

    resp1 = provider.complete(CompletionRequest(prompt="p1", node_id="node_1"))
    resp2 = provider.complete(CompletionRequest(prompt="p2", node_id="node_2"))
    resp3 = provider.complete(CompletionRequest(prompt="p3", node_id="node_3"))

    assert json.loads(resp1.content)["story"] == "Custom story 1"
    assert json.loads(resp2.content)["story"] == "Custom story 2"
    assert "Deterministic story" in resp3.content


def test_mock_provider_simulated_errors():
    """Verify error injection in MockProvider for rate limits and auth failures."""
    rate_lim_prov = MockProvider(simulate_rate_limit=True)
    with pytest.raises(LLMRateLimitError):
        rate_lim_prov.complete(CompletionRequest(prompt="test"))

    auth_prov = MockProvider(simulate_auth_error=True)
    with pytest.raises(LLMAuthenticationError):
        auth_prov.complete(CompletionRequest(prompt="test"))

    server_prov = MockProvider(simulate_server_error=True)
    with pytest.raises(LLMProviderError):
        server_prov.complete(CompletionRequest(prompt="test"))


def test_deterministic_fallback_provider():
    """Verify DeterministicFallbackProvider operates 100% offline without credentials."""
    provider = DeterministicFallbackProvider()
    req = CompletionRequest(
        prompt="Summarize node",
        node_id="python:billing/invoice.py::InvoiceParser.parse",
    )
    resp = provider.complete(req)

    assert resp.model == "deterministic-ast-v1"
    assert resp.total_tokens > 0

    parsed = LLMProvider.extract_json(resp.content)
    assert parsed is not None
    assert parsed["source"] == "deterministic"
    assert "InvoiceParser.parse" in parsed["summary"]


def test_extract_json_utilities():
    """Verify LLMProvider.extract_json extracts JSON from raw strings, code fences, and text."""
    # 1. Plain JSON string
    assert LLMProvider.extract_json('{"key": "value"}') == {"key": "value"}

    # 2. Markdown fence with json label
    fence_1 = """
    Here is the requested analysis:
    ```json
    {
        "status": "success",
        "score": 95
    }
    ```
    End of response.
    """
    assert LLMProvider.extract_json(fence_1) == {"status": "success", "score": 95}

    # 3. Markdown fence without language label
    fence_2 = "```\n{\"nested\": {\"flag\": true}}\n```"
    assert LLMProvider.extract_json(fence_2) == {"nested": {"flag": True}}

    # 4. JSON embedded in prose without code block
    prose = "The result payload is: {\"total\": 42} as requested."
    assert LLMProvider.extract_json(prose) == {"total": 42}

    # 5. Invalid / empty inputs return None
    assert LLMProvider.extract_json("") is None
    assert LLMProvider.extract_json("not valid json at all") is None


def test_provider_factory():
    """Verify get_llm_provider factory returns appropriate provider adapter."""
    mock_p = get_llm_provider("mock")
    assert isinstance(mock_p, MockProvider)

    fallback_p = get_llm_provider("fallback")
    assert isinstance(fallback_p, DeterministicFallbackProvider)

    with pytest.raises(ValueError):
        get_llm_provider("unsupported_provider_xyz")


def test_groq_provider_missing_key(monkeypatch):
    """Verify GroqProvider raises LLMAuthenticationError when no API key is available."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY_1", raising=False)
    monkeypatch.delenv("GROQ_API_KEY_2", raising=False)
    monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
    with pytest.raises(LLMAuthenticationError):
        GroqProvider(api_key=None, load_env=False)


def test_groq_provider_live_completion():
    """Verify live Groq API completions when GROQ_API_KEY is configured in .env."""
    load_env_file()
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        pytest.skip("GROQ_API_KEY not set in environment or .env; skipping live test")

    provider = GroqProvider(api_key=api_key)
    caps = provider.capabilities()
    assert caps.supports_structured_outputs is True

    req = CompletionRequest(
        prompt='Return a JSON object with key "status" set to "verified" and "source" set to "groq". No other text.',
        tier=ModelTier.FAST,
        max_tokens=60,
    )
    try:
        resp = provider.complete(req)
    except LLMRateLimitError:
        pytest.skip("Groq rate-limited (429); skipping live completion")

    assert resp.content
    assert resp.prompt_tokens > 0
    assert resp.completion_tokens > 0
    assert resp.latency_ms > 0

    parsed = LLMProvider.extract_json(resp.content)
    assert parsed is not None
    assert parsed.get("status") == "verified"
    assert parsed.get("source") == "groq"
