"""Groq API provider adapter using OpenAI-compatible chat completions interface."""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from repopeek.llm.base import LLMProvider
from repopeek.llm.env import load_env_file
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


class GroqProvider(LLMProvider):
    """High-speed inference adapter communicating with Groq via standard HTTP completions."""

    DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_TIER_MODELS = {
        ModelTier.FAST: "qwen/qwen3.8-27b",
        ModelTier.BALANCED: "qwen/qwen3.8-27b",
        ModelTier.STRONG: "openai/gpt-oss-120b",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        tier_models: Optional[Dict[ModelTier, str]] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        load_env: bool = True,
    ) -> None:
        if load_env:
            load_env_file()
        self.api_key = api_key if api_key is not None else os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise LLMAuthenticationError(
                "GROQ_API_KEY not found. Pass api_key or set GROQ_API_KEY environment variable."
            )

        self.base_url = (base_url or os.environ.get("GROQ_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        # Model tier mappings
        self.tier_models = dict(self.DEFAULT_TIER_MODELS)
        if tier_models:
            self.tier_models.update(tier_models)

        # Allow environment overrides
        if os.environ.get("GROQ_MODEL_FAST"):
            self.tier_models[ModelTier.FAST] = os.environ["GROQ_MODEL_FAST"]
        if os.environ.get("GROQ_MODEL_BALANCED"):
            self.tier_models[ModelTier.BALANCED] = os.environ["GROQ_MODEL_BALANCED"]
        if os.environ.get("GROQ_MODEL_STRONG"):
            self.tier_models[ModelTier.STRONG] = os.environ["GROQ_MODEL_STRONG"]

    def model_for_tier(self, tier: ModelTier) -> str:
        """Resolve abstract tier to concrete Groq model name."""
        return self.tier_models.get(tier, self.DEFAULT_TIER_MODELS[ModelTier.FAST])

    def capabilities(self) -> ProviderCapabilities:
        """Capabilities supported by the Groq LPU engine."""
        return ProviderCapabilities(
            supports_structured_outputs=True,
            supports_json_mode=True,
            supports_prompt_caching=True,
            supports_batch_api=True,
            available_models=list(set(self.tier_models.values())),
        )

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute chat completion request with exponential backoff on transient errors."""
        model = self.model_for_tier(request.tier)
        endpoint = f"{self.base_url}/chat/completions"

        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        if request.response_format:
            payload["response_format"] = request.response_format

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "RepoPeek/0.1.0",
        }

        body_bytes = json.dumps(payload).encode("utf-8")
        attempt = 0
        backoff = 1.0

        while attempt <= self.max_retries:
            attempt += 1
            t0 = time.perf_counter()
            req = urllib.request.Request(endpoint, data=body_bytes, headers=headers)

            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw_data = resp.read().decode("utf-8")
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    data = json.loads(raw_data)

                    choice = data["choices"][0]
                    content = choice["message"]["content"] or ""
                    usage = data.get("usage", {})

                    return CompletionResponse(
                        content=content,
                        model=data.get("model", model),
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                        cached_tokens=usage.get("prompt_cache_hit_tokens", 0),
                        latency_ms=latency_ms,
                    )

            except urllib.error.HTTPError as err:
                status = err.code
                err_body = err.read().decode("utf-8", errors="replace")

                if status in (401, 403):
                    raise LLMAuthenticationError(f"Groq API authentication failed ({status}): {err_body}")
                elif status == 404:
                    raise LLMModelNotFoundError(f"Groq model '{model}' not found: {err_body}")
                elif status == 429:
                    if attempt > self.max_retries:
                        raise LLMRateLimitError(f"Groq API rate limit exceeded after {self.max_retries} retries: {err_body}")
                    sleep_time = backoff
                    if hasattr(err, "headers") and err.headers and err.headers.get("Retry-After"):
                        try:
                            sleep_time = max(float(err.headers.get("Retry-After")), 0.5)
                        except Exception:
                            pass
                    else:
                        import re
                        m = re.search(r"try again in ([\d\.]+)s", err_body)
                        if m:
                            try:
                                sleep_time = max(float(m.group(1)) + 0.1, 0.5)
                            except Exception:
                                pass
                    time.sleep(sleep_time)
                    backoff = max(backoff * 1.5, sleep_time)
                elif 500 <= status < 600:
                    if attempt > self.max_retries:
                        raise LLMProviderError(f"Groq server error ({status}) after {self.max_retries} retries: {err_body}")
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    raise LLMProviderError(f"Groq API HTTP error {status}: {err_body}")

            except (urllib.error.URLError, TimeoutError, OSError) as net_err:
                if attempt > self.max_retries:
                    raise LLMProviderError(f"Groq network connection error: {net_err}")
                time.sleep(backoff)
                backoff *= 2.0

        raise LLMProviderError("Max retries exceeded while calling Groq API.")
