---
id: req-provenance
type: requirement
title: Semantic Provenance
summary: Every semantic node must retain traceable pointers to the exact source file,
  line range, deterministic node IDs, and confidence score that produced it.
status: planned
tags: [mvp, semantic, provenance]
code_refs: [repopeek/enrichment/]
depends_on: ['[[con-no-hallucination]]', '[[req-deterministic-extraction]]', '[[req-semantic-enrichment]]']
affects: ['[[data-node-businessprocess]]', '[[data-node-story]]', '[[feat-provenance-binding]]',
  '[[req-mvp-success-criteria]]']
last_verified: 2026-10-03
source: "_sources/architecture_documentation.md \xA74 Provenance"
---
# Semantic Provenance

## Purpose
Prevents semantic nodes from floating free of their evidence. Any agent or developer traversing the graph can trace a business claim back to the exact code line that generated it.

## Behavior / Contract
Every `BusinessProcess` and `Story` node must carry:
- `source_filepath` — relative path of originating file
- `line_range` — `[start_line, end_line]`
- `target_node_ids` — list of deterministic node IDs that grounded this inference
- `confidence` — float `[0.0, 1.0]`
- `provenance_commit` — git commit hash (**TBD** — see [[moc-open-questions]] Q3)

## Impact (blast radius)
- **Depends on:** [[req-semantic-enrichment]], [[req-deterministic-extraction]]
- **Affects (downstream):** [[feat-provenance-binding]], [[data-node-businessprocess]], [[data-node-story]]
- **If this changes, also review:** [[feat-query-cli]] (traversal output must surface provenance)

## Decisions & Constraints
[[con-no-hallucination]]

## Open questions
- `provenance_commit` implementation is TBD. See [[moc-open-questions]] Q3.

## Related
[[moc-features]]
