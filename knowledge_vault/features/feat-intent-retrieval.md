---
id: feat-intent-retrieval
type: feature
title: Intent-to-Symbol Task Matcher & SQLite FTS5 BM25 Index
summary: Offline 3-stage hybrid retrieval (AST identifier extraction, SQLite FTS5 BM25, and Reciprocal Rank Fusion k=60) resolving natural language tasks to candidate code symbols.
status: active
tags: [phase3, retrieval, intent, fts5, bm25, rrf]
code_refs: [repopeek/retrieval/__init__.py, repopeek/retrieval/intent.py, repopeek/storage/sqlite_cache.py, repopeek/query/engine.py, repopeek/cli.py, tests/test_retrieval.py]
depends_on: ['[[plan-phase-3]]', '[[feat-query-cli]]', '[[feat-graph-persistence]]', '[[comp-query]]', '[[moc-features]]']
affects: ['[[log-phase-3]]']
last_verified: 2026-10-05
---
# Intent-to-Symbol Task Matcher & SQLite FTS5 BM25 Index

## Purpose
Enables autonomous coding agents to resolve natural language engineering instructions (e.g. `"Fix the retry logic in PaymentProcessor.process_payment"`) into ranked candidate symbols without relying on external embeddings, GPUs, or vector databases.

## Architecture & Retrieval Pipeline
1. **Task Normalization & Entity Extraction (`repopeek.retrieval.intent.extract_task_identifiers`):**
   - Normalizes whitespace and strips syntactic punctuation while strictly preserving dotted symbols (`a.b.c`), quoted names (`"process_payment"`), file paths, and API routes.
   - Extracts PascalCase, camelCase (`retryCount`), snake_case, and constants while filtering noise using stop words and 35+ code-action verbs.
2. **Identifier Variant Generator (`generate_identifier_variants`):**
   - Synthesizes camelCase, snake_case, and space-delimited permutations from extracted symbols to enable resilient fuzzy matching across multi-word identifiers.
3. **AST Identifier Scorer (`_ast_identifier_search`):**
   - Directly scores nodes based on qualified name components (+10.0), symbol names (+6.0), parameter signatures (+4.0), and semantic stories (+1.0).
4. **SQLite FTS5 BM25 Table (`nodes_fts`):**
   - Weighted full-text search table created in `cache.db` with weights: `node_id` (2.0), `qualified_name` (5.0), `symbol_name` (5.0), `sig` (4.0), `file_path` (2.5), `story_text` (1.5).
   - Incrementally synced during single-file graph updates (`update_sqlite_file`).
5. **Reciprocal Rank Fusion ($k=60$):**
   - Blends AST identifier matches (weight 1.0) and FTS5 BM25 results (weight 0.9) into calibrated candidate symbols with transparent explanation reasons.

## Interfaces
- **Python API:** `GraphQueryEngine.resolve_task(task: str, limit: int = 20) -> List[Dict[str, Any]]`
- **CLI Flag:** `repopeek --resolve "<task>"`
