---
id: log-phase-2
type: log
title: Phase 2 Decision and Execution Log
summary: Running chronological log of decisions, research findings, dead ends, and open questions during Phase 2.
status: active
tags: [phase2, log, decisions]
code_refs: []
depends_on: ['[[plan]]']
affects: []
last_verified: 2026-10-04
---
# Phase 2 Decision and Execution Log

## 2026-10-03: Kickoff & Scope Alignment
- Git remote and `@modelcontextprotocol/server-github` configured.
- ADR updates: ADR-004 (JSON persistence), ADR-005 (hybrid parsing). Languages: Python, SQL, Shell, JSON, YAML.

## 2026-10-03: PR 2 — Scanner Agent & Canonical Schema
- Canonical schema: `NodeCard`, `NodeFacts`, `Span`, `Edge`, `CanonicalGraph` in `repopeek/models/schema.py`.
- Discovery engine: crawler, classifier, hasher, ignore filter in `repopeek/discovery/`. Fixture repo created.

## 2026-10-03: PR 3 — Python Parser Agent
- `PythonParser` in `repopeek/parsers/python.py`: AST definitions, calls, imports, complexity, embedded SQL.
- Syntax error resilience: fallback regex extracts definitions with `Confidence.UNRESOLVED`.

## 2026-10-03: Ponytail Configuration
- Installed Ponytail (`full` mode): YAGNI -> existing codebase -> stdlib -> minimal implementation.

## 2026-10-03: PR 4 — Polyglot Parsers
- `SqlParser` (SQLGlot Oracle/Postgres), `ShellParser` (stdlib `shlex`), `JsonConfigParser` & `YamlConfigParser`.

## 2026-10-03: PR 5 — Symbol Resolution & Canonical Graph Construction
- `SymbolResolver` and `GraphBuilder` assembling `CanonicalGraph` and NetworkX graph with initial lenses.

## 2026-10-03: PR 6 — Def-Use Data Flow, Config Readers & Cross-Language Bridges
- Variable def-use analysis, config bindings, cross-language bridges (Python SQL -> tables, Shell -> Python).
- Added `data`, `data_entity`, `config`, `process`, and `bridges` lenses, plus traversal impact utilities.

## 2026-10-03: PR 7 — Deterministic Graph Persistence & Git Provenance
- Git provenance (`get_git_provenance`, `compute_repo_blob_shas`), deterministic sharded JSON (`save_canonical_graph`, lenses, shards), and derived SQLite cache (`build_sqlite_cache`, `query_sqlite_impact`).

## 2026-10-04: PR 8 — LLM Provider Abstraction & Groq Adapter
- `LLMProvider` protocol, `GroqProvider` via stdlib `urllib.request` with exponential backoff on HTTP 429, `MockProvider`, `DeterministicFallbackProvider`, and provider factory. Live Groq verified.

## 2026-10-04: PR 9 — Story Cascade, Content-Hash Cache & Fact Verifier
- 5-tier cascade: `HierarchicalStoryGenerator` in `repopeek/enrichment/summarizer.py` (trivial bypass, content-hash cache, structured fast LLM, bottom-up map-reduce, strong escalation).
- Caching & validation: `StoryCache` in `repopeek/enrichment/cache.py`; `FactVerifier` in `repopeek/enrichment/verifier.py` preventing table/call hallucinations.
- Cost governor & CLI: `CostGovernor` in `repopeek/enrichment/governor.py`; `StoryPipeline` wired into CLI with `--offline` and `--dry-run` flags. 70/70 tests passing.

## 2026-10-04: PR 10 — Low-Context Retrieval & Context-Pack Service
- Graph query engine: `GraphQueryEngine` in `repopeek/query/engine.py` implementing `lookup`, `neighbors`, multi-hop `impact`, and cross-language `data_trace`.
- Context-pack service: `ContextPack` in `repopeek/query/pack.py` producing budget-governed (<500 tokens) prompt markdown blocks with node cards, stories, and blast-radius summaries.
- MCP server & CLI: `RepoPeekMCPServer` in `repopeek/query/mcp_server.py` exposing stdio JSON-RPC MCP tools; CLI `--lookup`, `--impact`, `--trace`, `--pack`, and `--serve-mcp` flags. 77/77 tests passing.

