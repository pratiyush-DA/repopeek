---
id: feat-graph-persistence
type: feature
title: Graph Persistence
summary: Serialize and deserialize the in-memory property graph to and from local disk storage.
status: active
tags: [phase4, storage, persistence]
code_refs: [repopeek/storage/json_store.py, repopeek/storage/provenance.py, repopeek/storage/sqlite_cache.py, repopeek/storage/__init__.py]
depends_on: ['[[adr-004-graph-persistence-tbd]]', '[[comp-graph]]', '[[data-graph-lenses]]',
  '[[feat-graph-construction]]', '[[feat-graph-validation]]']
affects: ['[[comp-query]]', '[[feat-query-cli]]']
last_verified: 2026-10-03
source: "_sources/task_list.md §Phase 4"
---
# Graph Persistence

## Purpose
Enables storing the constructed code intelligence graph locally so that subsequent queries, traversals, and enrichment runs do not require re-parsing the target codebase from scratch.

## Behavior / Contract
- **Input:** Canonical property graph (`CanonicalGraph`) with attached Git provenance and file blob SHAs.
- **Output:** Deterministic sharded JSON files (`graph.json`, `manifest.json`, `lenses/`, `shards/`) and derived SQLite cache (`cache.db`).
- **Deterministic JSON:** Keys sorted, indent=2, nulls excluded, SHA-256 integrity verification.
- **Materialized Lenses:** Subgraphs for `module`, `symbol`, `call`, `class`, `data`, `data_entity`, `config`, `process`, and `bridges`.
- **Atomic Writes:** Staged in temporary directories with atomic rename swap ensuring zero partial-write corruption.
- **SQLite Cache:** Ephemeral SQLite schema (`nodes`, `edges`, `metadata`) with recursive CTE query engine (`query_sqlite_impact`) for sub-millisecond impact traversal.

## Impact (blast radius)
- **Depends on:** [[feat-graph-construction]], [[comp-graph]]
- **Affects (downstream):** [[feat-query-cli]], [[comp-query]]
- **If this changes, also review:** [[adr-004-graph-persistence-tbd]], [[con-no-distributed-graph]], [[con-local-execution]]

## Related
[[moc-features]], [[moc-architecture]]
