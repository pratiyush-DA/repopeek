---
id: comp-graph
type: component
title: Graph Component
summary: Module repopeek/graph/ managing the in-memory NetworkX property graph, schema
  validation, and persistence.
status: active
tags: [phase4, component, graph]
code_refs: [repopeek/graph/builder.py, repopeek/graph/resolver.py, repopeek/graph/lenses.py, repopeek/graph/__init__.py, repopeek/storage/json_store.py, repopeek/storage/provenance.py, repopeek/storage/sqlite_cache.py, repopeek/storage/__init__.py]
depends_on: ['[[adr-001-networkx-local-graph]]', '[[adr-003-no-distributed-infra]]',
  '[[adr-004-graph-persistence-tbd]]', '[[adr-008-canonical-graph-lenses]]', '[[adr-009-provenance-incremental-updates]]',
  '[[adr-010-multi-agent-orchestration]]', '[[comp-config]]', '[[comp-parsers]]',
  '[[con-determinism]]', '[[con-local-execution]]', '[[con-no-distributed-graph]]',
  '[[data-edge-types]]', '[[data-graph-lenses]]', '[[data-node-file]]', '[[data-node-function]]',
  '[[data-node-jsonconfig]]', '[[data-node-repository]]', '[[data-node-sqlquery]]',
  '[[feat-graph-construction]]']
affects: ['[[comp-enrichment]]', '[[comp-query]]', '[[feat-graph-construction]]',
  '[[feat-graph-persistence]]', '[[feat-graph-validation]]', '[[feat-query-cli]]']
last_verified: 2026-10-03
source: "_sources/task_list.md §Phase 4"
---
# Graph Component

## Purpose
Owns the core property graph data structure. Assembles nodes and edges into an in-memory NetworkX directed graph, validates structural invariants against schema definitions, and persists/loads the graph to/from disk.

## Responsibilities
- Construct and manipulate NetworkX graph instances (`MultiDiGraph`).
- Validate nodes, edges, attributes, and types against `graph_schema.json`.
- Serialize the graph to disk (JSON / SQLite) and restore it for querying.
- Provide lookup, neighborhood queries, and subgraph extraction utilities.

## Interface / Contract
- `GraphBuilder.build_graph(parse_results: List[ParseResult]) -> NetworkXGraph`
- `GraphValidator.validate(graph: NetworkXGraph) -> ValidationReport`
- `GraphStorage.save(graph: NetworkXGraph, path: Path) -> None`
- `GraphStorage.load(path: Path) -> NetworkXGraph`
- Errors: Raises `GraphValidationError` if schema invariants are broken.

## Impact (blast radius)
- **Depends on:** [[comp-parsers]], [[comp-config]]
- **Affects (downstream):** [[comp-enrichment]], [[comp-query]], [[feat-graph-construction]], [[feat-graph-validation]], [[feat-graph-persistence]]
- **If this changes, also review:** [[adr-001-networkx-local-graph]], [[adr-004-graph-persistence-tbd]], [[data-edge-types]]
- **Data touched:** [[data-node-repository]], [[data-node-file]], [[data-node-function]], [[data-node-sqlquery]], [[data-node-jsonconfig]], [[data-node-businessprocess]], [[data-node-story]]

## Decisions & Constraints
[[adr-001-networkx-local-graph]], [[adr-003-no-distributed-infra]], [[adr-004-graph-persistence-tbd]], [[con-no-distributed-graph]]

## Related
[[moc-architecture]], [[moc-data-models]]
