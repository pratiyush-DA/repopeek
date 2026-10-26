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
last_verified: 2026-10-26
---

# Agent Model Context Protocol (MCP) Suite

## 1. Executive Summary & Purpose
The `RepoPeekMCPServer` implements the standard Model Context Protocol (MCP) specification over `stdio` using JSON-RPC 2.0 (server version 0.3.0). This allows autonomous coding assistants (such as Antigravity, Claude Desktop, Cursor, and custom agent sidecars) to interactively leverage RepoPeek's deterministic code property graph without running terminal commands or loading massive repository source contexts.

## 2. Exposed MCP Tool Suite
The server exposes 16 specialized intelligence tools:
1. `repopeek_context`: Compiles task-driven `ContextPackage` with progressive disclosure (`level 1/2/3`) and blast radius.
2. `repopeek_plan`: Risk-assessed engineering `ChangePlan` with creation-vs-modification intent.
3. `repopeek_impact`: Traversal confidence blast radius with exact citations (decorators, dynamic `getattr`).
4. `repopeek_routes`: Discovers fullstack HTTP endpoints, client calls, and cross-boundary linkages (`INVOKES`).
5. `repopeek_co_changes`: Historical git co-change patterns with shallow-clone fast-fail (<1ms) and disk caching.
6. `repopeek_resolve`: Resolves tasks to candidate symbols via AST + BM25 + RRF ($k=60$), top 5 compact items.
7. `repopeek_lookup`: Minimal symbol/ID inspection JSON cards (<70 tokens) with signatures and location.
8. `repopeek_neighbors`: Direct relational incoming/outgoing edge traversal.
9. `repopeek_data_trace`: Cross-language def-use tracing for variables and SQL tables.
10. `repopeek_context_pack`: Compact token-budget context packs (<500 tokens).
11. `repopeek_session_stats`: Session telemetry rollup of estimated token savings ([[feat-session-telemetry]]).
12. `repopeek_god_nodes`: Precomputed architectural hubs (<1ms), filtering builtins.
13. `repopeek_cycles`: Precomputed circular import detection (<1ms) strictly on code imports.
14. `repopeek_communities`: Precomputed modular clustering (<1ms) with top-N pagination.
15. `repopeek_suggest_questions`: Synthesizes actionable architectural review questions.
16. `repopeek_report`: Exports comprehensive markdown audit trail.

## 2b. Payload Discipline & Honest Empties
- **Budget guard:** Every response capped at ~15k chars, returning valid-JSON `{truncated, reason, preview}` if oversized.
- **Honest empties:** Tools return explanatory `note` instead of bare empty arrays when domain entities are absent.

## 3. Invocation Protocol
- Agents launch the server via `repopeek --serve-mcp`.
- Follows MCP JSON-RPC 2.0 handshake: `initialize` -> `notifications/initialized` -> `tools/list` -> `tools/call`.
- Completely deterministic, offline, and sub-10ms response time per query.

## 4. One-Click Assistant & Master Steering Rules Configuration
- **Command:** `repopeek install [cursor|claude|windsurf|antigravity|vscode|all]` (or `--install-mcp`, `repopeek rules all`).
- **MCP Registration:** Patches assistant JSON configs (`mcp.json`, `claude_desktop_config.json`, etc.) with `.bak` backups. For Antigravity, prioritizes workspace `.agents/mcp_config.json`.
- **Master Rule Injection:** Injects the Hybrid Decision Ladder and tool routing into client rules using idempotent `<!-- REPOPEEK-RULES:START -->` tags (with automatic migration of legacy `REPOPEEK-FIRST` tags):
  - **Cursor:** `.cursor/rules/repopeek.mdc` (`alwaysApply: true`) and `.cursorrules`.
  - **Claude Code:** `CLAUDE.md`.
  - **Windsurf:** `.windsurf/rules/repopeek.md` and `.windsurfrules`.
  - **Antigravity:** `.agents/rules/repopeek.md` and `~/.gemini/config/rules/repopeek.md`.
  - **Copilot / VS Code:** `.github/copilot-instructions.md`.
  - **Universal Standard:** `AGENTS.md`.
- **Steering Rule Structure:**
  1. **Mandatory Tool Routing:** Direct MCP tools, Meta/Lazy MCP indirection (`call_mcp_tool(ServerName="repopeek", ...)`), and terminal native CLI fallback (`repopeek --<cmd>`).
  2. **Competing Tool Negative Constraints:** Disables broad `grep_search`, `list_dir`, and raw file reading until RepoPeek returns zero results or errors.
  3. **Hybrid Decision Ladder:** Leaf edits skip RepoPeek; symbol contracts use `repopeek_lookup`; multi-file/unfamiliar code uses `repopeek_context`; concept searches use `repopeek_resolve`; shared interfaces use `repopeek_impact`; post-edit sync via `repopeek --update`.
