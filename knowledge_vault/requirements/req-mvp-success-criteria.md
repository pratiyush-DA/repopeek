---
id: req-mvp-success-criteria
type: requirement
title: MVP Success Criteria
summary: Six explicit acceptance criteria that define when the MVP is complete and
  proven.
status: planned
tags: [mvp, acceptance]
code_refs: []
depends_on: ['[[req-deterministic-extraction]]', '[[req-local-repo-analysis]]', '[[req-provenance]]',
  '[[req-queryable-graph]]', '[[req-semantic-enrichment]]']
affects: []
last_verified: 2026-10-03
source: "_sources/mvp_requirements.md \xA7MVP Success Criteria"
---
# MVP Success Criteria

## Purpose
Defines the finish line. All six criteria must pass before the MVP is declared complete.

## Criteria
1. **Inspect a small, local repository** — system accepts a local path and completes without error.
2. **Mechanically identify code structure** — functions, queries, configs, and relationships are found.
3. **Accurately represent relationships in a local graph** — graph output matches source code facts.
4. **Generate grounded semantic descriptions** — LLM summaries are tied to code, not invented.
5. **Maintain semantic provenance** — every semantic node has source file, lines, node IDs, confidence.
6. **Queryable by agent/developer** — a query for a code path or impact tree returns correct results.

## Impact (blast radius)
- **Depends on:** all other `req-*` notes
- **Affects (downstream):** nothing (this is the terminal acceptance gate)
- **If this changes, also review:** all feature and component notes

## Related
[[moc-features]], [[moc-architecture]]
