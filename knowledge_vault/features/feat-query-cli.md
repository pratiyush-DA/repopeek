---
id: feat-query-cli
type: feature
title: Query CLI and Low-Context Retrieval Service
summary: Low-context retrieval operations (lookup, neighbors, impact, data_trace, context_pack) and stdio MCP server for autonomous agents.
status: active
tags: [phase6, query, cli, mcp]
code_refs: [repopeek/query/engine.py, repopeek/query/pack.py, repopeek/query/mcp_server.py, repopeek/query/__init__.py, repopeek/viewer/server.py, repopeek/viewer/__init__.py, repopeek/cli.py]
depends_on: ['[[adr-011-mcp-interface]]', '[[comp-cli]]', '[[comp-graph]]', '[[comp-query]]',
  '[[data-node-card-spec]]', '[[feat-graph-construction]]', '[[feat-graph-persistence]]',
  '[[req-queryable-graph]]']
affects: ['[[comp-cli]]', '[[comp-query]]']
last_verified: 2026-10-04
source: "_sources/task_list.md §Phase 6"
---
# Query CLI and Low-Context Retrieval Service

## Purpose
Provides low-context retrieval operations, an interactive graph viewer, and a standard Model Context Protocol (MCP) server for autonomous AI coding agents operating with small context windows (<500 tokens).

## Core Retrieval Operations
1. **Node Lookup (`repopeek --lookup <query>` / `repopeek_lookup`):**
   - Retrieves atomic NodeCard (<80 tokens) by exact ID, qualified symbol suffix, or table name.
2. **Relational Neighborhood (`neighbors` / `repopeek_neighbors`):**
   - Inbound callers/readers and outbound callees/reads with confidence annotations.
3. **Upstream Impact Radius (`repopeek --impact <target>` / `repopeek_impact`):**
   - Multi-hop recursive reachability answering: "If I change X, which functions, files, and tables can break?"
4. **Cross-Language Data Trace (`repopeek --trace <entity>` / `repopeek_data_trace`):**
   - Traces variable assignments (`WRITES`) and usages (`READS`) across Python, SQL, and Shell pipelines.
5. **Context Pack Service (`repopeek --pack <targets...>` / `repopeek_context_pack`):**
   - Bundles the minimal sufficient sub-graph (<500 tokens) with one-line stories, signatures, and blast-radius summaries.
6. **Stdio MCP Server (`repopeek --serve-mcp`):**
   - Standard JSON-RPC protocol implementation connecting directly to external coding assistants.
7. **Interactive Web Graph Viewer (`repopeek --view`):**
   - Obsidian-style dark Canvas graph viewer serving local HTTP endpoints (`/api/graph`, `/api/impact`, `/api/pack`).
8. **Obsidian Vault Export & Query (`repopeek --export-obsidian [default] [--open]`, `repopeek --read-obsidian <symbol>`):**
   - Automatically detects active Obsidian vault (`default`) and exports atomic notes with wikilinks and color tags. `--open` launches Obsidian Desktop directly via OS URI. `read-obsidian` parses notes and links.

## Impact (blast radius)
- **Depends on:** [[feat-graph-persistence]], [[comp-graph]], [[req-queryable-graph]], [[adr-011-mcp-interface]]
- **Affects (downstream):** [[comp-query]], [[comp-cli]]
- **If this changes, also review:** [[req-mvp-success-criteria]], [[data-node-card-spec]]

## Related
[[moc-features]], [[moc-architecture]]
