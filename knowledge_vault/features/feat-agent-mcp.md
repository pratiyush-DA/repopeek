---
id: feat-agent-mcp
type: feature
title: Agent Model Context Protocol (MCP) Suite
summary: Exposes the full Phase 3 intelligence engine via stdio JSON-RPC MCP server with context compilation, change plans, blast radius, HTTP routes, and temporal co-change.
status: verified
tags: [mcp, agent, json-rpc, context-pack, blast-radius]
code_refs: [repopeek/query/mcp_server.py, repopeek/query/engine.py, repopeek/cli.py]
depends_on: ['[[feat-query-cli]]', '[[feat-context-compiler]]', '[[feat-traversal-confidence]]', '[[plan-phase-3]]']
affects: ['[[log-phase-3]]']
last_verified: 2026-10-06
---

# Agent Model Context Protocol (MCP) Suite

## 1. Executive Summary & Purpose
The `RepoPeekMCPServer` implements the standard Model Context Protocol (MCP) specification over `stdio` using JSON-RPC 2.0. This allows autonomous coding assistants (such as Antigravity, Claude Desktop, Cursor, and custom agent sidecars) to interactively leverage RepoPeek's deterministic code property graph without running terminal commands or loading massive repository source contexts.

## 2. Exposed MCP Tool Suite
The server exposes 10 standardized agent tools:
1. `repopeek_context`: Compiles natural language engineering tasks into budget-governed `ContextPackage`s with multi-tier progressive disclosure (`level 1/2/3`), constraints, and blast radius.
2. `repopeek_plan`: Generates a risk-assessed, step-by-step engineering change plan (`ChangePlan`) with dependency ordering and blast radius summaries.
3. `repopeek_impact`: Performs evidence-backed traversal confidence queries partitioned into direct, indirect, and excluded nodes with exact `file:line` citations.
4. `repopeek_routes`: Discovers fullstack HTTP route endpoints, client API calls (`fetch`, `axios`), and cross-boundary linkages (`INVOKES`).
5. `repopeek_co_changes`: Queries historical git commit co-change patterns and conditional probabilities $P(B|A)$.
6. `repopeek_resolve`: Resolves ambiguous natural language tasks into ranked candidate symbols via AST normalization + SQLite FTS5 BM25 + Reciprocal Rank Fusion ($k=60$).
7. `repopeek_lookup`: Fast symbol or ID inspection returning minimal JSON cards (<80 tokens) with optional source snippets.
8. `repopeek_neighbors`: Direct relational traversal returning incoming and outgoing edges.
9. `repopeek_data_trace`: Cross-language def-use tracing for variables and SQL database tables.
10. `repopeek_context_pack`: Compact token-budget-governed context packs (<500 tokens).

## 2b. Payload Discipline & Honest Empties
- **Systemic budget guard:** every tool response is capped at ~15k chars at the serialization
  boundary; an oversized payload is replaced with a valid-JSON `{truncated, reason, preview}`
  notice rather than a broken fragment (backstop over the per-tool caps and the blast-radius
  impact cap).
- **Honest empties:** `repopeek_routes` / `repopeek_data_trace` / `repopeek_co_changes` return an
  explanatory `note` when there is no web layer / data entity / git co-change history, instead of
  a bare empty payload.

## 3. Invocation Protocol
- Agents launch the server via `repopeek --serve-mcp`.
- Follows MCP JSON-RPC 2.0 handshake: `initialize` -> `notifications/initialized` -> `tools/list` -> `tools/call`.
- Completely deterministic, offline, and sub-10ms response time per query.
