---
id: comp-query
type: component
title: Query Component
summary: Module repopeek/query/ providing graph traversal algorithms, impact radius
  calculation, and path inspection.
status: planned
tags: [phase6, component, query]
code_refs: [repopeek/query/]
depends_on: ['[[comp-cli]]', '[[comp-enrichment]]', '[[comp-graph]]', '[[feat-graph-persistence]]',
  '[[feat-query-cli]]', '[[req-queryable-graph]]']
affects: ['[[comp-cli]]', '[[feat-query-cli]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 6"
---
# Query Component

## Purpose
Provides high-performance query algorithms and traversal mechanics on top of the saved property graph. Allows callers to inspect nodes, calculate forward/reverse call paths, and evaluate the transitive blast radius of code or database schema changes.

## Responsibilities
- Execute topological search and reachability queries across `CALLS`, `IMPORTS`, and `READS` relationships.
- Compute impact trees indicating all functions, queries, or processes affected by modifying a given file or function.
- Format traversal results into hierarchical display trees or structured JSON dictionaries.

## Interface / Contract
- `GraphQueryEngine.get_node(node_id: str) -> Optional[Node]`
- `GraphQueryEngine.trace_calls(func_name: str, direction: str = "downstream") -> CallTree`
- `GraphQueryEngine.calculate_impact(target_id: str) -> ImpactReport`
- Inputs: Node identifiers, traversal direction, search filters
- Outputs: Traversable graph path reports and impact sets

## Impact (blast radius)
- **Depends on:** [[comp-graph]]
- **Affects (downstream):** [[comp-cli]], [[feat-query-cli]]
- **If this changes, also review:** [[req-queryable-graph]]
- **Data touched:** All nodes and edges in [[moc-data-models]]

## Decisions & Constraints
[[req-queryable-graph]], [[con-determinism]]

## Related
[[moc-architecture]]
