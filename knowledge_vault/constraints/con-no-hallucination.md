---
id: con-no-hallucination
type: constraint
title: Anti-Hallucination and Grounding Rule
summary: Undocumented behaviors, schema fields, or business logic must never be invented;
  unknowns must be flagged as TBD.
status: active
tags: [constraint, quality, llm, provenance]
affects: ['[[comp-enrichment]]', '[[feat-provenance-binding]]', '[[feat-semantic-enrichment]]',
  '[[req-provenance]]']
last_verified: 2026-10-03
source: "_sources/cursorrules.md \xA7Agent Operating Rules"
depends_on: []
---
# Anti-Hallucination and Grounding Rule

## Rule
If a behavior, schema field, dependency, architectural decision, or product requirement is not documented or directly inferable from existing code, the system must NOT invent it. It must be explicitly marked as "TBD", given a low confidence score, or escalated for human clarification.

## Rationale
AI agents reading code intelligence graphs must be able to distinguish between concrete verified facts and speculative summaries. Hallucinated architecture leads to cascading bugs in automated coding pipelines.

## What it prohibits
- Inventing caller relationships or table dependencies not present in code or SQL.
- Generating `BusinessProcess` or `Story` nodes without concrete `IMPLEMENTS` edges to source files.
- Filling missing schema fields with fictional data instead of `null` or explicit TBD markers.

## Enforcement
- Invariant checks during graph validation ensuring every semantic node has valid deterministic anchors.
- LLM prompt engineering with strict grounding constraints.

## Related
[[req-provenance]], [[feat-provenance-binding]], [[moc-open-questions]]
