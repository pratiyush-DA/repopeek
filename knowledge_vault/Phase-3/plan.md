---
id: plan-phase-3
type: plan
title: Phase 3 Execution Plan — Context Compiler & Change-Impact Engine
summary: Implementation roadmap for Phase 3 transitioning RepoPeek into a task-driven context compiler and blast-radius engine.
status: active
tags: [phase3, planning, architecture, context-compiler]
code_refs: [repopeek/retrieval/intent.py, repopeek/storage/sqlite_cache.py, repopeek/query/engine.py, repopeek/cli.py, repopeek/graph/blast_radius.py, repopeek/context/compiler.py, repopeek/parsers/typescript.py]
depends_on: ['[[moc-architecture]]', '[[moc-features]]']
affects: ['[[log-phase-3]]', '[[feat-intent-retrieval]]', '[[feat-traversal-confidence]]', '[[feat-context-compiler]]', '[[feat-typescript-parser]]']
last_verified: 2026-10-05
---

# Phase 3 Execution Plan — Context Compiler & Change-Impact Engine

## 1. Executive Summary & Objective
Phase 2 delivered the polyglot code property graph (Python, SQL, Shell, JSON/YAML), deterministic JSON/SQLite persistence, 5-tier story cascade, and sub-500-token context packs. Phase 3 elevates RepoPeek into an **agent-neutral Context Compiler and Change-Impact Engine**, shifting from symbol-level queries to natural language task compilation (`repopeek context "<task>"` and `repopeek plan "<task>"`).

## 2. Core Architectural Principles
1. **Deterministic Structure First:** Local AST, SQLite FTS5 BM25, and graph traversal operate completely offline without LLM, GPU, or vector DB.
2. **Task Intent Resolution:** 3-stage hybrid resolver (AST identifier variant normalization + FTS5 BM25 + Reciprocal Rank Fusion $k=60$).
3. **Calibrated Confidence Scoring:** Multi-hop path confidence $PathConfidence = \min(0.99, \prod c_i \cdot \exp(-0.25(h-1)))$ with multi-path combination $1 - \prod(1 - P_i)$ and distance decay.
4. **Canonical Context Package:** Structured JSON artifact and Markdown rendering with progressive disclosure, token budget allocation, and multi-tier constraints (code, docstrings, tests, config, history).
5. **Git Temporal Intelligence:** Commit log mining (`git log --no-merges --name-only`), exponential half-life decay ($t_{1/2}=180$ days), and pairwise co-change frequency $P(B|A)$.
6. **Polyglot Boundary Bridge:** Tree-sitter TypeScript AST matcher connecting client `fetch()` / Axios calls to Python FastAPI endpoints.

## 3. Pull Request Delivery Sequence
- **PR 12: Intent-to-Symbol Task Matcher & SQLite FTS5 Index:** AST identifier extractor, FTS5 virtual table, and RRF rank fusion.
- **PR 13: Mathematical Traversal Confidence & Evidence-Backed Blast Radius:** Multi-hop confidence decay, exact `file:line` citations, and direct/indirect/excluded partitioning.
- **PR 14: Context Compiler, Constraint Extractor & Change Plan Generator:** Canonical JSON `ContextPackage`, progressive disclosure Markdown, constraint parser, and `cc context` / `cc plan` CLI.
- **PR 15: Polyglot Expansion: TypeScript & JavaScript Parser:** `.ts`, `.tsx`, `.js`, `.jsx` AST parser extracting classes, functions, imports, and calls.
- **PR 16: Git Temporal Intelligence & Co-Change Matrix:** Git commit history miner, exponential time decay, and `CO_CHANGED_WITH` relational edges.
- **PR 17: Cross-Language HTTP Boundary:** TypeScript client calls (`fetch`/Axios) to FastAPI route handler bridge with `:param` normalization.
- **PR 18: Agent MCP Suite & Incremental Watch Daemon:** Agent-facing MCP tools (`repopeek_context`, `repopeek_plan`, `repopeek_impact`) and background `repopeek watch` daemon.

## 4. Execution Tracking
All decisions, benchmarks, and progress are logged in [[log-phase-3]].
