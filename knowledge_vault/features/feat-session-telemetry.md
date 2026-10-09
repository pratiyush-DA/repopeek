---
id: feat-session-telemetry
type: feature
title: MCP Session Savings Telemetry
summary: Session-rollup telemetry on the MCP server reporting estimated tokens and file reads the agent avoided, with optional OpenTelemetry export and no network egress by default.
status: verified
tags: [mcp, telemetry, opentelemetry, savings, estimate]
code_refs: [repopeek/query/telemetry.py, repopeek/query/mcp_server.py]
depends_on: ['[[feat-agent-mcp]]', '[[feat-context-compiler]]']
affects: []
last_verified: 2026-10-09
---

# MCP Session Savings Telemetry

## 1. Purpose
Reports how much context RepoPeek saved an agent over a session: estimated tokens and file reads avoided. Lives entirely inside the MCP server, so it is agent-agnostic (Kiro, Cursor, Claude Desktop, etc.) and needs no host-agent cooperation.

## 2. Estimate, not measurement
The server cannot observe the host agent's prompt boundaries or the reads it avoided, so savings are **modeled**. For a `repopeek_context` call the baseline is the compiler's `raw_file_tokens` (full-file read equivalent of the affected files, see [[feat-context-compiler]]); savings = baseline − tokens returned. `repopeek_context_pack` uses an average-file model (~1200 tokens/file). Lookup/impact/trace calls count tokens returned but add no savings estimate.

## 3. Accumulator (`TelemetrySession`)
A single long-lived instance per server process is the session rollup (Option A). Counters: total calls, tokens returned, `tokens_saved_estimate`, `files_avoided_estimate`, and per-tool calls/latency. `reduction_pct = saved / (returned + saved)`. All counters are plain Python and always work, independent of OpenTelemetry.

## 4. Surfaces
- **`repopeek_session_stats` MCP tool** (markdown/json) — on-demand rollup; excluded from its own counters so reading it never inflates it.
- **stderr shutdown summary** — printed in `run_stdio`'s finally block, so savings show even if the agent never calls the tool. stderr keeps the stdio JSON-RPC channel clean. See [[feat-agent-mcp]].

## 5. OpenTelemetry (optional, no egress by default)
Opt-in via `REPOPEEK_OTEL=1` (console exporter, needs the `telemetry` extra) or `REPOPEEK_OTEL_ENDPOINT` (OTLP/HTTP, needs `telemetry-otlp`). Missing SDK degrades silently to the pure-Python path. Metrics: `repopeek.tool.calls`, `repopeek.tool.latency_ms`, `repopeek.pack.tokens_returned`, `repopeek.tokens_saved_estimate`, `repopeek.files_avoided_estimate`.
