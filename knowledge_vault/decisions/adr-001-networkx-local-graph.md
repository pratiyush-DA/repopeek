---
id: adr-001-networkx-local-graph
type: decision
title: NetworkX In-Memory Property Graph for MVP
summary: Use NetworkX as the core in-memory property graph engine to keep Repopeek
  lightweight, local, and embeddable.
status: accepted
tags: [architecture, graph, adr]
affects: ['[[comp-graph]]', '[[con-no-distributed-graph]]', '[[feat-graph-construction]]']
last_verified: 2026-10-03
source: "_sources/architecture_documentation.md \xA7Phase 4"
depends_on: ['[[con-no-distributed-graph]]']
---
# ADR-001: NetworkX In-Memory Property Graph for MVP

## Status
Accepted

## Context
Repopeek requires a graph data structure to model files, functions, SQL queries, JSON configs, business processes, and their relationships. External graph databases introduce heavy operational overhead, Docker dependencies, or service credentials incompatible with local CLI tooling.

## Decision
Use Python's `networkx` library (`MultiDiGraph`) as the primary graph representation in memory. Graph validation will be enforced via custom schema validators against `graph_schema.json`.

## Alternatives considered
- **Neo4j / Memgraph:** Powerful query languages (Cypher), but requires running a separate daemon/container and violates local simplicity rules.
- **SQLite / custom adjacency list:** Lightweight, but lacks built-in graph traversal algorithms (shortest paths, ancestor/descendant traversal).
- **Rust/C++ graph bindings:** Faster for massive repos, but complicates cross-platform installation and pip packaging.

## Consequences
- **Positive:** Zero external server dependencies; pip installable everywhere; native Python object manipulation; rich graph algorithm library.
- **Negative:** Entire graph resides in RAM; scaling limited to repositories that fit comfortably in memory (sufficient for target MVP codebases).

## Notes
[[con-no-distributed-graph]], [[moc-decisions]]
