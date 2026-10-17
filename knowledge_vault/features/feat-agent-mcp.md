---
id: feat-agent-mcp
type: feature
title: Agent Model Context Protocol (MCP) Suite
summary: Exposes the full Phase 3 intelligence engine via stdio JSON-RPC MCP server with context compilation, change plans, blast radius, HTTP routes, and temporal co-change.
status: verified
tags: [mcp, agent, json-rpc, context-pack, blast-radius]
code_refs: [repopeek/query/mcp_server.py, repopeek/query/engine.py, repopeek/cli.py, repopeek/query/telemetry.py, repopeek/mcp_installer.py]
depends_on: ['[[feat-query-cli]]', '[[feat-context-compiler]]', '[[feat-traversal-confidence]]', '[[plan-phase-3]]', '[[feat-graph-analysis]]', '[[feat-graph-report]]']
affects: ['[[log-phase-3]]', '[[feat-session-telemetry]]']
last_verified: 2026-10-18
---

# Agent Model Context Protocol (MCP) Suite

## 1. Executive Summary & Purpose
The `RepoPeekMCPServer` implements the standard Model Context Protocol (MCP) specification over `stdio` using JSON-RPC 2.0 (server version 0.3.0). This allows autonomous coding assistants (such as Antigravity, Claude Desktop, Cursor, and custom agent sidecars) to interactively leverage RepoPeek's deterministic code property graph without running terminal commands or loading massive repository source contexts.

## 2. Exposed MCP Tool Suite
The server exposes 16 specialized intelligence tools:
1. `repopeek_context`: Compiles natural language engineering tasks into budget-governed `ContextPackage`s with multi-tier progressive disclosure (`level 1/2/3`), constraints, and blast radius. Best for multi-file features and unfamiliar code.
2. `repopeek_plan`: Generates a risk-assessed, step-by-step engineering change plan (`ChangePlan`) with creation-vs-modification intent detection and blast radius summaries.
3. `repopeek_impact`: Performs evidence-backed traversal confidence queries partitioned into direct, indirect, and excluded nodes with exact `file:line` citations (includes class decorator, dynamic `getattr`, and registry linkages).
4. `repopeek_routes`: Discovers fullstack HTTP route endpoints, client API calls (`fetch`, `axios`), and cross-boundary linkages (`INVOKES`).
5. `repopeek_co_changes`: Queries historical git commit co-change patterns with shallow-clone fast-fail (<1ms) and precomputed disk caching.
6. `repopeek_resolve`: Resolves ambiguous natural language tasks into ranked candidate symbols via AST normalization + SQLite FTS5 BM25 + Reciprocal Rank Fusion ($k=60$), defaulting to 5 compact items with code-first weighting.
7. `repopeek_lookup`: Ultra-compact symbol or ID inspection returning minimal JSON cards (<70 tokens) with signature, location, and blast radius.
8. `repopeek_neighbors`: Direct relational traversal returning incoming and outgoing edges.
9. `repopeek_data_trace`: Cross-language def-use tracing for variables and SQL database tables with token-anchored exact matching and reader/writer deduplication.
10. `repopeek_context_pack`: Compact token-budget-governed context packs (<500 tokens) with progressive hard budget enforcement.
11. `repopeek_session_stats`: Session rollup of usage with *estimated* context savings; details in [[feat-session-telemetry]].
12. `repopeek_god_nodes`: Precomputed architectural hubs ranking (<1ms), filtering external builtins.
13. `repopeek_cycles`: Precomputed circular import dependency detection (<1ms) strictly on code imports.
14. `repopeek_communities`: Precomputed modular clustering (<1ms) with size-ranked pagination (top 10 communities by default).
15. `repopeek_suggest_questions`: Synthesizes actionable architectural review questions.
16. `repopeek_report`: Exports comprehensive markdown audit trail utilizing precomputed analytical blocks.

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

## 4. One-Click Client Auto-Configuration
- Command: `repopeek mcp install --client [cursor|claude|windsurf|antigravity|vscode]` (or default `all`).
- Safely discovers and patches assistant configuration files (`mcp.json`, `claude_desktop_config.json`, etc.) with automatic `.bak` backups.
