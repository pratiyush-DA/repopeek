---
id: plan-phase-2
type: plan
title: Phase 2 Execution Plan and Architectural Decisions
summary: Implementation plan for Phase 2 kickoff, synthesizing owner constraints,
  research benchmarks, and PR sequence.
status: active
tags: [phase2, planning, architecture]
code_refs: []
depends_on: ['[[moc-architecture]]', '[[moc-decisions]]', '[[moc-features]]']
affects: ['[[log]]', '[[res-groq-capabilities]]', '[[res-parsing-stack]]', '[[res-prior-art]]',
  '[[res-story-cost-control]]']
last_verified: 2026-10-03
---
# Phase 2 Execution Plan and Architectural Decisions

## 1. Executive Summary & Phase 1 Baseline
Phase 1 established project scaffolding, `RepopeekConfig` in `repopeek/config.py`, CLI harness in `repopeek/cli.py`, 10/10 passing tests, and the 51-note verified knowledge vault. Phase 2 transitions RepoPeek into an end-to-end multi-agent code intelligence engine extracting a canonical property graph across Python, SQL, shell, JSON, and YAML with materialised lens graphs.

## 2. Locked Decisions (Owner Constraints)
1. **Graph Persistence (ADR-004):** Canonical JSON with deterministic key sorting and stable node/edge ordering. Optional SQLite cache for fast traversal.
2. **Parsing Stack (ADR-005):** Multi-language parsing via tree-sitter core, stdlib AST for high-fidelity Python semantics, SQLGlot for SQL, tree-sitter-bash for shell, stdlib json/ruamel.yaml for config schemas.
3. **Provenance Commit Field:** Git commit SHA binding (`git rev-parse HEAD`), dirty flag, blob SHAs, and non-git fallback.
4. **LLM Provider:** Groq as initial provider via OpenAI-compatible endpoint (`api.groq.com/openai/v1`), wrapped in pluggable `LLMProvider` abstraction protocol.
5. **Supported Languages:** Python (`.py`), SQL (`.sql` and embedded), Shell (`.sh`, `.bash`), JSON (`.json`), YAML (`.yaml`, `.yml`).
6. **Output Shape:** One canonical property graph with materialised lens graphs (Module, Symbol, Call, Class, Data, Entity, Config, Process, Exception, Test, Bridges).
7. **LLM Cost Strategy:** 5-tier cascade: (1) Deterministic AST template, (2) Content-hash cache, (3) Cheap-model structured summary, (4) Bottom-up hierarchical summarisation, (5) Strong model for hotspots.
8. **Architecture:** Explicit typed task graph on asyncio without heavy framework bloat.
9. **GitHub MCP Server:** Integration configured using `@modelcontextprotocol/server-github`.

## 3. Pre-Implementation Research Agenda
- **3.1 Parsing Benchmark:** Benchmark `tree-sitter`, stdlib `ast`, and `sqlglot` on small, medium, and syntax-broken repositories.
- **3.2 Prior Art Analysis:** Review `Codebase-Memory` (arXiv 2603.27277), `CodeGraphContext`, `RepoGraph`, and `CodexGraph`.
- **3.3 Cost Control & Groq Optimization:** Verify Groq API capabilities (structured outputs, prompt caching, batch API discount).
- **3.4 SQLite vs JSON Benchmark:** Benchmark traversal performance for multi-hop blast-radius queries.

## 4. Pull Request & Delivery Sequence
- **PR 1: Docs & ADR Refresh:** Record updated ADR-001 through ADR-005, new ADR-006 through ADR-012, research notes, and initial plan.
- **PR 2: Scanner & Canonical Schema:** File crawler, ignore filter, hash computer, canonical node/edge schema, and fixture repo.
- **PR 3: Multi-Language Parsing Stack:** Tree-sitter + AST integration for Python with benchmarks.
- **PR 4: SQL, Shell, JSON, YAML Parsers:** SQLGlot with dialect detection, tree-sitter-bash, JSON/ruamel.yaml keypath extractors.
- **PR 5: Symbol Resolver & Core Lenses:** Cross-file name resolution and core lens materialisation.
- **PR 6: Data, Config, Process Graphs & Bridges:** Variable def-use flow, env/config readers, cross-language bridges.
- **PR 7: Graph Persistence & Provenance Engine:** Canonical JSON serialization, atomicity, git provenance, and incremental indexing.
- **PR 8: LLM Provider Abstraction:** `LLMProvider` protocol, Groq adapter, OpenAI adapter, mock adapter, and deterministic fallback.
- **PR 9: Story Cascade, Cache & Verifier:** Content-hash caching, hierarchical summarizer, fact verifier, and cost governor.
- **PR 10: Low-Context Retrieval & Context-Pack Service:** `lookup`, `neighbors`, `impact`, `data_trace`, `context_pack`, and MCP server.
- **PR 11: Final Polish & Dogfooding:** Full run on RepoPeek itself, golden test validation, and comprehensive metrics report.

## 5. Working Log
Ongoing decisions, benchmarks, and notes are maintained in [[log-phase-2]].
