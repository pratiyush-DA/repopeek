---
id: req-semantic-enrichment
type: requirement
title: Semantic Enrichment via LLM
summary: An LLM must augment the deterministic graph with business-level nodes (BusinessProcess,
  Story) grounded in existing deterministic nodes.
status: planned
tags: [mvp, semantic, llm]
code_refs: [repopeek/enrichment/]
depends_on: ['[[req-deterministic-extraction]]']
affects: ['[[feat-provenance-binding]]', '[[feat-semantic-enrichment]]', '[[req-mvp-success-criteria]]',
  '[[req-provenance]]', '[[req-queryable-graph]]']
last_verified: 2026-10-03
source: "_sources/architecture_documentation.md \xA72 Semantic Layer"
---
# Semantic Enrichment via LLM

## Purpose
The semantic overlay adds business understanding that cannot be mechanically derived. It is built bottom-up (function → module → process) to minimize hallucination.

## Behavior / Contract
- LLM operates only on top of existing deterministic nodes — never on raw source text alone.
- Bottom-up pipeline: function summaries → module-level interactions → BusinessProcess/Story nodes.
- Every semantic node must carry provenance pointers (file, lines, node IDs, confidence score).
- LLM output that cannot be grounded in a deterministic node is discarded.

## Impact (blast radius)
- **Depends on:** [[req-deterministic-extraction]], [[feat-graph-construction]]
- **Affects (downstream):** [[feat-semantic-enrichment]], [[feat-provenance-binding]], [[data-node-businessprocess]], [[data-node-story]]
- **If this changes, also review:** [[req-provenance]], [[con-no-hallucination]]

## Decisions & Constraints
[[con-no-hallucination]], [[moc-open-questions]] (Q4 — LLM choice TBD)

## Open questions
- Which LLM / SDK is used? See [[moc-open-questions]] Q4.

## Related
[[moc-features]]
