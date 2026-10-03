---
id: feat-graph-persistence
type: feature
title: Graph Persistence
summary: Serialize and deserialize the in-memory property graph to and from local
  disk storage.
status: planned
tags: [phase4, storage, persistence]
code_refs: [repopeek/graph/]
depends_on: ['[[adr-004-graph-persistence-tbd]]', '[[comp-graph]]', '[[data-graph-lenses]]',
  '[[feat-graph-construction]]', '[[feat-graph-validation]]']
affects: ['[[comp-query]]', '[[feat-query-cli]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 4"
---
# Graph Persistence

## Purpose
Enables storing the constructed code intelligence graph locally so that subsequent queries, traversals, and enrichment runs do not require re-parsing the target codebase from scratch.

## Behavior / Contract
- Input: In-memory NetworkX graph instance
- Output: Persistent local file representation on disk
- Format: JSON node-link structure (or local SQLite file) — see [[adr-004-graph-persistence-tbd]]
- Storage Path: Configured via [[comp-config]] (e.g. `.repopeek/graph.json` or `output/graph.json`)
- Atomic Writes: Writes must be atomic or safely handled to avoid corrupted graph files.

## Impact (blast radius)
- **Depends on:** [[feat-graph-construction]], [[comp-graph]]
- **Affects (downstream):** [[feat-query-cli]], [[comp-query]]
- **If this changes, also review:** [[adr-004-graph-persistence-tbd]], [[con-no-distributed-graph]], [[con-local-execution]]

## Open questions
- Decision on primary storage backend (JSON vs SQLite): [[adr-004-graph-persistence-tbd]]

## Related
[[moc-features]], [[moc-architecture]]
