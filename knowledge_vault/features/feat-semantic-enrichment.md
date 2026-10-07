---
id: feat-semantic-enrichment
type: feature
title: Semantic Enrichment
summary: 5-tier story generation cascade, content-hash caching, bottom-up hierarchical summarization, and anti-hallucination fact verification.
status: active
tags: [phase5, enrichment, llm]
code_refs: [repopeek/enrichment/cache.py, repopeek/enrichment/verifier.py, repopeek/enrichment/governor.py, repopeek/enrichment/templates.py, repopeek/enrichment/summarizer.py, repopeek/enrichment/pipeline.py, repopeek/enrichment/__init__.py, repopeek/llm/groq.py, repopeek/llm/factory.py]
depends_on: ['[[adr-007-story-cost-cascade]]', '[[comp-enrichment]]', '[[con-no-hallucination]]',
  '[[data-node-businessprocess]]', '[[data-node-story]]', '[[feat-graph-construction]]',
  '[[feat-graph-validation]]', '[[req-semantic-enrichment]]']
affects: ['[[comp-enrichment]]', '[[data-node-businessprocess]]', '[[data-node-story]]',
  '[[feat-provenance-binding]]']
last_verified: 2026-10-06
source: "_sources/architecture_documentation.md §Semantic Enrichment"
---
# Semantic Enrichment

## Purpose
Bridges raw AST code facts with human and low-context agent conceptual understanding by executing a controlled 5-tier story generation cascade with content-hash caching and anti-hallucination verification.

## 5-Tier Story Generation Cascade
1. **Tier 1 — Trivial Code Filter (Zero Cost):** Syntactic getters/setters, constants, and complexity-1 routines receive deterministic templates via `DeterministicStoryBuilder` without invoking an LLM.
2. **Tier 2 — Content-Hash Cache:** Cached by `hash(content_hash + model_tier + prompt_version)` via `StoryCache`. Unchanged symbols are never re-queried across runs.
3. **Tier 3 — Cheap Model Structured Summary:** Non-trivial leaf functions invoke fast models (`qwen/qwen3.8-27b` or `llama-3.1-8b-instant`) with constrained JSON decoding and cached prompt prefixes.
4. **Tier 4 — Hierarchical Bottom-Up Map-Reduce:** Compound nodes (classes and modules) are summarized from child method/function stories, never raw bulk source code.
5. **Tier 5 — Strong Model Escalation:** High-complexity architectural hotspots (complexity >= 10) escalate to frontier models under strict budget governance.

## Anti-Hallucination Fact Verifier
Every candidate LLM story is verified against AST facts via `FactVerifier`:
- Verifies length (<= 60 words) and rejects raw code or fence dumps.
- Rejects stories claiming database operations on tables not present in `facts.reads` or `facts.writes`.
- Rejects stories claiming external network/service calls when `facts.calls == 0`.
- Downgrades failed candidates to deterministic templates with `confidence="medium"`.

## Cost Governor & Budget Enforcement
`CostGovernor` tracks prompt, completion, and cached tokens, enforcing `--max-tokens` and `--max-cost` hard caps with automated fallback to deterministic templates upon exhaustion. LLM overlay is optional: `external_symbol`/`variable`/`json_config`/`yaml_config`/`command` stay templates; LLM only top-K hotspots (`REPOPEEK_LLM_MAX_NODES`, default 200) with heartbeat logs. Groq uses `GROQ_API_KEY` plus optional `_2`/`_3` (separate orgs for RPM; same-org still isolates 429). Default concurrency 2. Never log keys.

## Impact (blast radius)
- **Depends on:** [[feat-graph-construction]], [[feat-graph-validation]], [[req-semantic-enrichment]], [[adr-007-story-cost-cascade]]
- **Affects (downstream):** [[feat-provenance-binding]], [[data-node-businessprocess]], [[data-node-story]], [[comp-enrichment]]
- **If this changes, also review:** [[req-provenance]], [[con-no-hallucination]]

## Related
[[moc-features]], [[moc-architecture]]
