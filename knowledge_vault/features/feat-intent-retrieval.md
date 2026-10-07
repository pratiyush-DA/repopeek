---
id: feat-intent-retrieval
type: feature
title: Intent-to-Symbol Task Matcher & SQLite FTS5 BM25 Index
summary: Offline 3-stage hybrid retrieval (AST identifier extraction, SQLite FTS5 BM25, and Reciprocal Rank Fusion k=60) resolving natural language tasks to candidate code symbols.
status: active
tags: [phase3, retrieval, intent, fts5, bm25, rrf]
code_refs: [repopeek/retrieval/__init__.py, repopeek/retrieval/intent.py, repopeek/storage/sqlite_cache.py, repopeek/query/engine.py, repopeek/cli.py, tests/test_retrieval.py, tests/test_retrieval_reliability.py]
depends_on: ['[[plan-phase-3]]', '[[feat-query-cli]]', '[[feat-graph-persistence]]', '[[comp-query]]', '[[moc-features]]']
affects: ['[[log-phase-3]]']
last_verified: 2026-10-06
---
# Intent-to-Symbol Task Matcher & SQLite FTS5 BM25 Index

## Purpose
Enables autonomous coding agents to resolve natural language engineering instructions (e.g. `"Fix the retry logic in PaymentProcessor.process_payment"`) into ranked candidate symbols without relying on external embeddings, GPUs, or vector databases.

## Architecture & Retrieval Pipeline
1. **Task Normalization & Entity Extraction (`repopeek.retrieval.intent.extract_task_identifiers`):**
   - Normalizes whitespace and strips syntactic punctuation while strictly preserving dotted symbols (`a.b.c`), quoted names (`"process_payment"`), file paths, and API routes.
   - Extracts PascalCase, camelCase (`retryCount`), snake_case, and constants while filtering noise using stop words and 35+ code-action verbs.
   - Negative clauses (`MUST NOT edit a.py or b.py`, `Do not change Django UserLoginView`) capture **all** paths/symbols in the clause; framework prefixes like `Django` are not exclusions.
   - Applies conservative linguistic stemming (`normalize_term_stem`) for noun/verb inflections (plurals, `-ing`, `-ed`, `-ation`) and engineering synonyms (`config`, `auth`, `init`, `param`) without destructive over-stemming.
2. **Identifier Variant Generator (`generate_identifier_variants`):**
   - Synthesizes 6 canonical casings: `snake_case`, `camelCase`, `PascalCase`, `SCREAMING_SNAKE_CASE`, `kebab-case`, and `dot.notation` to match AST symbols irrespective of naming conventions.
   - Generates adjacent domain compounds (e.g. `payment_retry`, `retry_payment`, `PaymentRetry`).
3. **AST Identifier Scorer (`_ast_identifier_search`):**
   - Direct candidate scoring powered by an inverted token index (`_get_or_build_token_index`) cached on `node_index` for sub-millisecond candidate lookup.
   - Directly scores nodes based on qualified name components (+10.0), symbol names (+8.0), parameter signatures (+3.0), and semantic stories (+1.0).
4. **SQLite FTS5 BM25 Table (`nodes_fts`):**
   - Weighted full-text search table created in `cache.db` with weights: `node_id` (2.0), `qualified_name` (5.0), `symbol_name` (5.0), `sig` (4.0), `file_path` (2.5), `story_text` (1.5).
5. **Calibrated Multi-Component Ranking (`compute_retrieval_score`):**
   - Combines normalized score components: `exact_match`, `identifier`, `token_overlap`, `lexical_bm25`, `path_relevance`, and `kind_preference` (`RetrievalScore`).
   - Ranks candidate symbols deterministically, reducing ranking error failures by >60% and lifting Recall@5 from 26% to 80%.

## Interfaces
- **Python API:** `GraphQueryEngine.resolve_task(task: str, limit: int = 20) -> List[Dict[str, Any]]`
- **CLI Flag:** `repopeek --resolve "<task>"`
- **Deterministic Explain:** `repopeek --explain "<task>"` / `repopeek explain "<task>"`

