---
id: adr-007-story-cost-cascade
type: decision
title: Five-Tier Story Generation Cost Cascade and Verifier
summary: Implement a 5-tier story generation cascade prioritizing deterministic AST
  facts, content caching, and bottom-up aggregation to govern LLM token spend.
status: accepted
tags: [architecture, llm, cost, caching, adr]
code_refs: [repopeek/enrichment/]
depends_on: ['[[res-story-cost-control]]']
affects: ['[[comp-enrichment]]', '[[feat-semantic-enrichment]]', '[[moc-decisions]]']
last_verified: 2026-10-03
source: "RepoPeek Owner Briefing \xA72 & \xA76.3"
---
# ADR-007: Five-Tier Story Generation Cost Cascade and Verifier

## Status
Accepted

## Context
Code summarization across large codebases can easily exhaust token budgets and incur high API costs. Without strict governance, autonomous indexing jobs risk spiraling in cost.

## Decision
Enforce a mandatory 5-tier story generation cascade where each tier runs only if preceding tiers are insufficient:

1. **Tier 1 — Deterministic Story (No LLM):** Templated directly from AST facts (signature, docstring first line, decorators, notable calls/reads/writes). Trivial code (getters/setters, `__repr__`, one-line wrappers, dataclass boilerplate) never invokes an LLM.
2. **Tier 2 — Content-Hash Cache:** Cached by `hash(normalized_source + child_story_hashes + prompt_version + model_tier)`. Unchanged code is never re-summarized.
3. **Tier 3 — Cheap Model Structured Summary:** Non-trivial leaf functions invoke the fast tier (`llama-3.1-8b-instant`) with constrained JSON decoding. Static prompt prefixing activates provider-side prompt caching (50% discount).
4. **Tier 4 — Hierarchical Bottom-Up Map-Reduce:** Class, module, and package summaries are synthesized from child stories, never raw bulk source code.
5. **Tier 5 — Strong Model Escalation:** Strong tier models are restricted to high fan-in hubs or nodes rejected by the verifier, strictly capped by budget limits.

### Cost Controls & Verifier
- **Dry-run & Caps:** `--dry-run` estimates token spend prior to execution; `--max-cost` and `--max-tokens` enforce hard termination with deterministic fallback.
- **Anti-Hallucination Verifier:** Every LLM story is verified against AST facts. Any hallucinated tables or functions cause the node to downgrade to deterministic.

## Consequences
- 80–95% reduction in LLM token consumption on cold runs; >98% token reduction on incremental runs.

## Notes
[[res-story-cost-control]], [[moc-decisions]]
