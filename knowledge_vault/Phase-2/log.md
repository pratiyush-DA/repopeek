---
id: log-phase-2
type: log
title: Phase 2 Decision and Execution Log
summary: Running chronological log of decisions, research findings, dead ends, and
  open questions during Phase 2.
status: active
tags: [phase2, log, decisions]
code_refs: []
depends_on: ['[[plan]]']
affects: []
last_verified: 2026-10-03
---
# Phase 2 Decision and Execution Log

## 2026-10-03: Phase 2 Kickoff & Scope Alignment
- Git remote configured; `@modelcontextprotocol/server-github` enabled in `mcp_config.json`.
- ADR updates: ADR-004 (JSON persistence), ADR-005 (hybrid parsing). Scope set to Python, SQL (Oracle), Shell, JSON, YAML.

## 2026-10-03: PR 2 — Scanner Agent & Canonical Schema
- Canonical schema: `NodeCard`, `NodeFacts`, `Span`, `Edge`, `CanonicalGraph` in `repopeek/models/schema.py`.
- Discovery engine: crawler, MIME classifier, hasher, `.repopeekignore` matcher in `repopeek/discovery/`.
- Test fixture created at `tests/fixtures/sample_repo/`. 20/20 tests passing.

## 2026-10-03: PR 3 — Python Parser Agent
- `PythonParser` in `repopeek/parsers/python.py`: AST definitions, calls, imports, cyclomatic complexity, embedded SQL.
- Syntax error resilience: fallback regex extracts partial definitions with `Confidence.UNRESOLVED`. 25/25 tests passing.

## 2026-10-03: Ponytail Configuration
- Installed Ponytail plugin via `agy plugin install https://github.com/DietrichGebert/ponytail`.
- Active mode: `full`. Enforced YAGNI -> existing codebase -> stdlib -> installed deps -> minimal implementation.

## 2026-10-03: PR 4 — Polyglot Parsers
- `SqlParser`: `sqlglot` with Oracle default, Postgres fallback, table definitions, queries, and column references.
- `ShellParser`: stdlib `shlex`, pipeline commands, script invocations, env vars.
- `JsonConfigParser` & `YamlConfigParser`: dot-notated key flattening and script links. 35/35 tests passing.

## 2026-10-03: PR 5 — Symbol Resolution & Canonical Graph Construction
- `SymbolResolver`: resolves cross-file imports, calls, inheritance, script runs, and SQL tables. Flags external libs.
- `GraphBuilder`: aggregates multi-language parse results into `CanonicalGraph` and `networkx.MultiDiGraph`.
- Multi-lens projections: `get_module_lens`, `get_symbol_lens`, `get_call_lens`, `get_class_lens`. 42/42 tests passing.

