---
id: req-queryable-graph
type: requirement
title: Queryable Graph Interface
summary: A developer or agent must be able to query the generated graph to understand
  a specific code path, impact tree, or business process without reading raw source.
status: planned
tags: [mvp, agent-interface]
code_refs: [repopeek/query/]
depends_on: ['[[req-deterministic-extraction]]', '[[req-semantic-enrichment]]']
affects: ['[[comp-query]]', '[[feat-query-cli]]', '[[req-mvp-success-criteria]]']
last_verified: 2026-10-03
source: "_sources/mvp_requirements.md \xA7MVP Success Criteria"
---
# Queryable Graph Interface

## Purpose
The final output is only useful if it can be interrogated. This requirement ensures the knowledge built by Repopeek is accessible to both human developers and AI coding agents.

## Behavior / Contract
- Queries the unified graph (deterministic + semantic layers combined).
- Supports: node lookup, call-chain traversal, impact trees (what breaks if X changes?), and business-process-to-code mapping.
- Interface: CLI in MVP; programmatic API is future scope.

## Impact (blast radius)
- **Depends on:** [[feat-graph-construction]], [[feat-graph-persistence]], [[feat-semantic-enrichment]]
- **Affects (downstream):** [[feat-query-cli]], [[comp-query]]
- **If this changes, also review:** [[req-mvp-success-criteria]]

## Decisions & Constraints
[[adr-004-graph-persistence-tbd]] (format affects how CLI reads data)

## Related
[[moc-features]]
