---
id: comp-enrichment
type: component
title: Enrichment Component
summary: Module repopeek/llm/ executing LLM-based semantic enrichment, model tiering, and story generation.
status: active
code_refs: [repopeek/llm/base.py, repopeek/llm/groq.py, repopeek/llm/mock.py, repopeek/llm/fallback.py, repopeek/llm/factory.py, repopeek/llm/__init__.py, repopeek/enrichment/cache.py, repopeek/enrichment/verifier.py, repopeek/enrichment/governor.py, repopeek/enrichment/templates.py, repopeek/enrichment/summarizer.py, repopeek/enrichment/pipeline.py, repopeek/enrichment/__init__.py]
depends_on: ['[[adr-006-llm-provider-abstraction]]', '[[adr-007-story-cost-cascade]]',
  '[[comp-config]]', '[[comp-graph]]', '[[con-no-hallucination]]', '[[data-node-businessprocess]]',
  '[[data-node-story]]', '[[feat-semantic-enrichment]]', '[[res-groq-capabilities]]',
  '[[res-story-cost-control]]', '[[run-swap-llm-provider]]']
affects: ['[[comp-query]]', '[[feat-provenance-binding]]', '[[feat-semantic-enrichment]]']
last_verified: 2026-10-06
source: "_sources/task_list.md §Phase 5"
---
# Enrichment Component

## Purpose
Orchestrates LLM prompts and responses to add semantic layers atop deterministic code facts. Synthesizes business process flows and user stories, while binding verifiable line-level provenance and confidence scores.

## Responsibilities
- Decouple vendor inference APIs through the unified `LLMProvider` protocol (`repopeek/llm/`).
- Execute structured completions via Groq LPU engine (`GroqProvider`) or offline mocks (`MockProvider`, `DeterministicFallbackProvider`).
- Dynamically resolve model tiers (`fast`, `balanced`, `strong`) avoiding hardcoded model names in application logic.
- Robustly parse structured JSON output from raw text, code fences, and embedded blocks.
- Handle transient network errors and rate limits (HTTP 429) with exponential backoff and jitter.

## Interface / Contract
- `LLMProvider.complete(request: CompletionRequest) -> CompletionResponse`
- `LLMProvider.capabilities() -> ProviderCapabilities`
- `LLMProvider.extract_json(content: str) -> Optional[Dict[str, Any]]`
- `get_llm_provider(name: Optional[str]) -> LLMProvider`

## Impact (blast radius)
- **Depends on:** [[comp-graph]], [[comp-config]], [[adr-006-llm-provider-abstraction]]
- **Affects (downstream):** [[comp-query]], [[feat-semantic-enrichment]], [[feat-provenance-binding]]
- **If this changes, also review:** [[req-provenance]], [[con-no-hallucination]], [[res-groq-capabilities]]
- **Data touched:** [[data-node-businessprocess]], [[data-node-story]], [[data-edge-types]]

## Related
[[moc-architecture]]
