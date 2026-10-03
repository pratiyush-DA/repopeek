---
id: comp-query
type: component
title: Query Component
summary: Module repopeek/query/ providing graph traversal algorithms, impact radius calculation, and context packs.
status: active
tags: [phase6, component, query]
code_refs: [repopeek/query/engine.py, repopeek/query/pack.py, repopeek/query/mcp_server.py, repopeek/query/__init__.py]
depends_on: ['[[comp-cli]]', '[[comp-enrichment]]', '[[comp-graph]]', '[[data-node-card-spec]]',
  '[[feat-graph-persistence]]', '[[feat-query-cli]]', '[[req-queryable-graph]]']
affects: ['[[comp-cli]]', '[[feat-query-cli]]']
last_verified: 2026-10-04
source: "_sources/task_list.md §Phase 6"
---
# Query Component

## Purpose
Provides high-performance query algorithms and traversal mechanics on top of the canonical property graph and SQLite cache. Allows callers to inspect atomic node cards, calculate blast radius, trace def-use data flows, and bundle budget-governed context packs.

## Responsibilities
- Execute topological search and reachability queries across `CALLS`, `IMPORTS`, `READS`, and `WRITES` relationships.
- Compute multi-hop blast radius trees answering "If I change X, what breaks?"
- Produce minimal budget-governed `ContextPack` payloads (<500 tokens) with markdown serialization for low-context agents.
- Expose retrieval operations over stdio JSON-RPC Model Context Protocol (MCP) server.

## Interface / Contract
- `GraphQueryEngine.lookup(query: str) -> Optional[NodeCard]`
- `GraphQueryEngine.neighbors(node_id: str, direction: str) -> Dict[str, Any]`
- `GraphQueryEngine.impact(target_query: str, max_depth: int) -> Dict[str, Any]`
- `GraphQueryEngine.data_trace(entity_query: str) -> Dict[str, Any]`
- `GraphQueryEngine.context_pack(targets: List[str], token_budget: int) -> ContextPack`
- `RepoPeekMCPServer.run_stdio() -> None`

## Impact (blast radius)
- **Depends on:** [[comp-graph]], [[comp-enrichment]], [[feat-graph-persistence]]
- **Affects (downstream):** [[comp-cli]], [[feat-query-cli]]
- **If this changes, also review:** [[req-queryable-graph]]
- **Data touched:** All nodes and edges in [[moc-data-models]]

## Related
[[moc-architecture]]
