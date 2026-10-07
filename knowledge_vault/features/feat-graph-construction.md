---
id: feat-graph-construction
type: feature
title: Graph Construction
summary: Assemble parsed deterministic nodes and relational edges into a unified NetworkX directed property graph with cross-file symbol resolution and lenses.
status: active
tags: [phase4, graph, networkx]
code_refs: [repopeek/graph/builder.py, repopeek/graph/resolver.py, repopeek/graph/lenses.py, repopeek/graph/identity.py, repopeek/graph/__init__.py]
depends_on: ['[[adr-001-networkx-local-graph]]', '[[comp-graph]]', '[[data-edge-types]]',
  '[[data-node-file]]', '[[data-node-repository]]', '[[feat-json-parser]]', '[[feat-python-parser]]',
  '[[feat-sql-parser]]', '[[req-deterministic-extraction]]']
affects: ['[[comp-graph]]', '[[feat-graph-persistence]]', '[[feat-graph-validation]]',
  '[[feat-query-cli]]', '[[feat-semantic-enrichment]]', '[[feat-typescript-parser]]', '[[feat-git-temporal]]', '[[feat-http-bridge]]', '[[feat-watch-daemon]]']
last_verified: 2026-10-06
source: "_sources/task_list.md §Phase 4"
---
# Graph Construction

## Purpose
Aggregates all deterministic nodes (Repository, File, Function, SqlQuery, JsonConfig) and relational edges (DEFINED_IN, CALLS, IMPORTS, READS) into a single in-memory NetworkX directed multigraph (`nx.MultiDiGraph` or `nx.DiGraph`).

## Behavior / Contract
- Input: Parsed elements from [[feat-python-parser]], [[feat-sql-parser]], and [[feat-json-parser]]
- Output: An in-memory NetworkX graph instance where:
  - Every node has a unique `id`, `type`, and corresponding metadata attributes
  - Every edge has a `type` attribute (`DEFINED_IN`, `CALLS`, `IMPORTS`, `READS`)
- Root Anchor: Creates the top-level [[data-node-repository]] node and connects all [[data-node-file]] nodes to it.
- Deduplication: Node IDs are deterministically derived from file paths and code symbols to prevent duplicate insertion.

## Impact (blast radius)
- **Depends on:** [[feat-python-parser]], [[feat-sql-parser]], [[feat-json-parser]], [[req-deterministic-extraction]]
- **Affects (downstream):** [[feat-graph-validation]], [[feat-graph-persistence]], [[feat-semantic-enrichment]], [[feat-query-cli]], [[comp-graph]]
- **If this changes, also review:** [[adr-001-networkx-local-graph]], [[con-determinism]], [[data-edge-types]]

## Related
[[moc-features]], [[moc-architecture]]
