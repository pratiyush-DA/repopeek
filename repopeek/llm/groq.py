"""Groq API provider adapter using OpenAI-compatible chat completions interface."""

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

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


def collect_groq_api_keys(explicit: Optional[str] = None) -> List[str]:
    """Load GROQ_API_KEY plus optional GROQ_API_KEY_2 / _3 without logging values."""
    if explicit:
        return [explicit]
    names = ("GROQ_API_KEY", "GROQ_API_KEY_1", "GROQ_API_KEY_2", "GROQ_API_KEY_3")
    keys: List[str] = []
    seen = set()
    for name in names:
        val = (os.environ.get(name) or "").strip()
        if not val or val == "your_groq_api_key_here" or val in seen:
            continue
        seen.add(val)
        keys.append(val)
    return keys


class GroqProvider(LLMProvider):
    """High-speed inference adapter with optional multi-key 429 isolation."""

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
        max_retries: int = 2,
        load_env: bool = True,
    ) -> None:
        if load_env:
            load_env_file()
        self._keys = collect_groq_api_keys(api_key)
        if not self._keys:
            raise LLMAuthenticationError(
                "GROQ_API_KEY not found. Pass api_key or set GROQ_API_KEY environment variable."
            )
        self.api_key = self._keys[0]
        self._cool_until = [0.0] * len(self._keys)
        self._rr = 0
        self._lock = threading.Lock()

        self.base_url = (base_url or os.environ.get("GROQ_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        self.tier_models = dict(self.DEFAULT_TIER_MODELS)
        if tier_models:
            self.tier_models.update(tier_models)

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

    def _acquire_key_index(self) -> Optional[int]:
        now = time.monotonic()
        with self._lock:
            n = len(self._keys)
            for _ in range(n):
                idx = self._rr % n
                self._rr += 1
                if now >= self._cool_until[idx]:
                    return idx
            soonest = min(self._cool_until)
        wait = max(0.0, min(soonest - now, 2.0))
        if wait > 0:
            time.sleep(wait)
        now = time.monotonic()
        with self._lock:
            for i, cool in enumerate(self._cool_until):
                if now >= cool:
                    return i
        return None

    def _cool_key(self, idx: int, seconds: float) -> None:
        with self._lock:
            self._cool_until[idx] = max(self._cool_until[idx], time.monotonic() + max(0.5, seconds))

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Execute chat completion; 429 cools one key so siblings can continue."""
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

        body_bytes = json.dumps(payload).encode("utf-8")
        last_err: Optional[Exception] = None
        attempts = self.max_retries * max(1, len(self._keys))

        for _ in range(attempts):
            idx = self._acquire_key_index()
            if idx is None:
                raise LLMRateLimitError("All Groq API keys are cooling after 429 responses.")
            headers = {
                "Authorization": f"Bearer {self._keys[idx]}",
                "Content-Type": "application/json",
                "User-Agent": "RepoPeek/0.1.0",
            }
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
                    self._cool_key(idx, 60.0)
                    last_err = LLMAuthenticationError(f"Groq API authentication failed ({status})")
                    continue
                if status == 404:
                    raise LLMModelNotFoundError(f"Groq model '{model}' not found: {err_body}")
                if status == 429:
                    sleep_time = 2.0
                    if hasattr(err, "headers") and err.headers and err.headers.get("Retry-After"):
                        try:
                            sleep_time = max(float(err.headers.get("Retry-After")), 0.5)
                        except Exception:
                            pass
                    else:
                        m = re.search(r"try again in ([\d\.]+)s", err_body)
                        if m:
                            try:
                                sleep_time = max(float(m.group(1)) + 0.1, 0.5)
                            except Exception:
                                pass
                    self._cool_key(idx, min(sleep_time, 30.0))
                    last_err = LLMRateLimitError("Groq API rate limit exceeded")
                    continue
                if 500 <= status < 600:
                    self._cool_key(idx, 1.5)
                    last_err = LLMProviderError(f"Groq server error ({status})")
                    continue
                raise LLMProviderError(f"Groq API HTTP error {status}: {err_body}")
            except (urllib.error.URLError, TimeoutError, OSError) as net_err:
                self._cool_key(idx, 1.0)
                last_err = LLMProviderError(f"Groq network connection error: {net_err}")
                continue

        if last_err:
            raise last_err
        raise LLMProviderError("Max retries exceeded while calling Groq API.")
