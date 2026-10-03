---
id: adr-006-llm-provider-abstraction
type: decision
title: Pluggable LLM Provider Abstraction and Model Tiering
summary: Abstract LLM interactions behind a provider interface with abstract model
  tiers (fast, balanced, strong) and Groq as the initial adapter.
status: accepted
tags: [architecture, llm, groq, abstraction, adr]
code_refs: [repopeek/enrichment/]
depends_on: ['[[res-groq-capabilities]]']
affects: ['[[comp-enrichment]]', '[[moc-decisions]]', '[[run-swap-llm-provider]]']
last_verified: 2026-10-03
source: "RepoPeek Owner Briefing \xA72 & \xA76.2"
---
# ADR-006: Pluggable LLM Provider Abstraction and Model Tiering

## Status
Accepted

## Context
RepoPeek uses Groq for high-speed, cost-effective inference in Phase 2. However, LLM providers, pricing, rate limits, and APIs evolve rapidly. Hardcoding Groq or specific model names into core code creates technical debt and prevents offline usage or provider migration.

## Decision
1. **Interface Contract:** Define an `LLMProvider` Protocol/ABC with methods:
   - `complete(request: CompletionRequest) -> CompletionResponse`
   - `batch_submit(requests: List[CompletionRequest]) -> str`
   - `batch_collect(batch_id: str) -> List[CompletionResponse]`
   - `capabilities: ProviderCapabilities`
2. **Adapters:**
   - `GroqProvider`: Uses Groq's OpenAI-compatible client (`https://api.groq.com/openai/v1`).
   - `OpenAICompatibleProvider`: Generic adapter for OpenAI, vLLM, DeepSeek, etc.
   - `MockProvider`: Offline fake provider for deterministic unit testing.
   - `LocalProvider`: Optional Ollama/local adapter for `--offline` analysis.
3. **Model Tiers:** Code references abstract tiers only (`fast`, `balanced`, `strong`), configured in `repopeek.toml`. Zero hardcoded model names or URLs in Python code.
4. **Transient Error Handling:** Exponential backoff with jitter on HTTP 429, concurrency cap, token bucket rate limiter, and automatic fallback to deterministic stories if retries fail.

## Alternatives considered
- **Direct Groq SDK binding:** Rejected because it couples application logic to a single vendor.
- **LangChain / LiteLLM:** Evaluated, but introduces heavy external dependency trees for what is cleanly achieved with standard HTTP / OpenAI client protocols.

## Consequences
- New providers can be added in under 30 lines of code.
- Test suite can run 100% offline using `MockProvider`.

## Notes
[[res-groq-capabilities]], [[run-swap-llm-provider]], [[moc-decisions]]
