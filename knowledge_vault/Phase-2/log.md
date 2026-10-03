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

## 2026-10-03: PR 6 — Def-Use Data Flow, Config Readers & Cross-Language Bridges
- Variable def-use flow: AST variable assignments, state mutations, and data reads/writes in `repopeek/parsers/python.py`.
- Config & env bindings: `SymbolResolver` resolves config keys (`database.dialect`) and env vars (`PIPELINE_ENV`) to config/script nodes.
- Cross-language bridges: Python embedded SQL statements resolve directly to SQL schema table cards; Shell and YAML script runs resolve to Python/Shell targets.
- Multi-lens materialisation: `get_data_lens`, `get_data_entity_lens`, `get_config_lens`, `get_process_lens`, and `get_bridges_lens` in `repopeek/graph/lenses.py`.
- Traversal utilities: `trace_variable_flow` and `trace_impact` for def-use inspection and upstream blast-radius queries. 49/49 tests passing.

## 2026-10-03: PR 7 — Deterministic Graph Persistence & Git Provenance
- Git-anchored provenance: `get_git_provenance` and `compute_repo_blob_shas` in `repopeek/storage/provenance.py` extract HEAD commit SHA, branch, and dirty status with non-git fallback and Git blob SHAs.
- Deterministic sharded persistence: `save_canonical_graph`, `load_canonical_graph`, `load_lens`, `load_manifest`, and `load_file_shard` in `repopeek/storage/json_store.py` emit deterministic JSON (`graph.json`, `manifest.json`, 9 lenses, and source shards) with atomic swap.
- Ephemeral SQLite traversal cache: `build_sqlite_cache` and recursive CTE engine `query_sqlite_impact` in `repopeek/storage/sqlite_cache.py`.
- End-to-end integration: `GraphBuilder.build_from_directory` auto-attaches provenance and blob SHAs; CLI indexes and persists artifacts. 56/56 tests passing.

## 2026-10-04: PR 8 — LLM Provider Abstraction & Groq Adapter
- Interface contract: `LLMProvider` abstract protocol in `repopeek/llm/base.py` with `CompletionRequest`, `CompletionResponse`, `ModelTier`, and `ProviderCapabilities`.
- Zero-dependency Groq adapter: `GroqProvider` in `repopeek/llm/groq.py` via stdlib `urllib.request` with exponential backoff on HTTP 429, Cloudflare header compatibility, model tier resolution, and live API verification.
- Testing & offline adapters: `MockProvider` in `repopeek/llm/mock.py` with error injection and history tracking; `DeterministicFallbackProvider` in `repopeek/llm/fallback.py` for offline zero-cost AST summaries.
- Environment & factory: `load_env_file` in `repopeek/llm/env.py` and `get_llm_provider` in `repopeek/llm/factory.py`. 64/64 tests passing.



