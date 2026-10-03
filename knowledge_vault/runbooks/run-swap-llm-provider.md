---
id: run-swap-llm-provider
type: runbook
title: Swapping or Adding an LLM Provider (< 30 Lines)
summary: Step-by-step developer runbook showing how to plug in a new LLM provider
  implementation in under 30 lines.
status: active
tags: [runbook, llm, provider, extension]
code_refs: [repopeek/enrichment/]
depends_on: ['[[adr-006-llm-provider-abstraction]]']
affects: ['[[comp-enrichment]]']
last_verified: 2026-10-03
source: "RepoPeek Owner Briefing \xA76.2"
---
# Swapping or Adding an LLM Provider (< 30 Lines)

## Interface Definition
Every provider implements the `LLMProvider` protocol:

```python
from typing import Protocol
from repopeek.enrichment.models import CompletionRequest, CompletionResponse, ProviderCapabilities

class LLMProvider(Protocol):
    capabilities: ProviderCapabilities
    def complete(self, request: CompletionRequest) -> CompletionResponse: ...
```

## Adding a Custom Provider (Example: Custom Ollama / vLLM in 22 Lines)

```python
# repopeek/enrichment/providers/custom.py
import requests
from repopeek.enrichment.models import CompletionRequest, CompletionResponse, ProviderCapabilities

class CustomLocalProvider:
    def __init__(self, endpoint: str = "http://localhost:11434/api/generate"):
        self.endpoint = endpoint
        self.capabilities = ProviderCapabilities(supports_structured=True, supports_caching=False)

    def complete(self, req: CompletionRequest) -> CompletionResponse:
        payload = {"model": req.model, "prompt": req.prompt, "stream": False, "format": "json"}
        res = requests.post(self.endpoint, json=payload, timeout=req.timeout_s).json()
        return CompletionResponse(content=res["response"], usage={"tokens": res.get("eval_count", 0)})
```

## Registration in `repopeek.toml`
Point configuration to the new provider without modifying core pipeline code:
```toml
[llm]
provider = "custom"
endpoint = "http://localhost:11434/api/generate"
[llm.tiers]
fast = "qwen2.5-coder:7b"
balanced = "qwen2.5-coder:14b"
strong = "qwen2.5-coder:32b"
```

## Related
[[adr-006-llm-provider-abstraction]], [[comp-enrichment]]
