# Component Responsibilities

This document defines the explicit contracts, operational boundaries, and non-responsibilities for every architecturally significant component in RepoPeek.

---

## 1. Discovery Subsystem (`repopeek.discovery`)

### Purpose
Scans repository disk trees, applies deterministic filtering, classifies file types, and computes cryptographic hashes.

### Responsibilities
- Deterministic traversal: Sorts directory and file lists alphabetically before processing.
- Ignore evaluation: Parses `.repopeekignore`, `.gitignore`, and enforces default exclude lists (`.git`, `node_modules`, `venv`, `__pycache__`, etc.).
- Binary detection: Inspects the initial 8KB chunk of files for null bytes (`\x00`).
- File cap enforcement: Skips files exceeding `max_file_size_kb` (default 2048 KB).
- Hash calculation: Computes SHA-256 and git-compatible blob SHAs (`blob <size>\0<content>`).

### Non-Responsibilities
- Does NOT parse code syntax or validate code semantics.
- Does NOT construct graph edges or node cards.
- Does NOT resolve symlinks outside the repository root.

### Key Symbols
- `discover_repository()` in [`crawler.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/crawler.py)
- `classify_file()`, `is_binary_file()` in [`classifier.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/classifier.py)
- `compute_file_hashes()`, `hash_content()` in [`hasher.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/hasher.py)
- `IgnoreRuleSet` in [`ignore.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/ignore.py)

---

## 2. Polyglot Parsers Subsystem (`repopeek.parsers`)

### Purpose
Performs deterministic syntactic analysis of source code into atomic `NodeCard` definitions and raw relational `Edge` records.

### Responsibilities
- Python (`PythonParser`): Extracts classes, functions, methods, imports, calls, parameter types, return annotations, exceptions raised/caught, variable writes/reads, and embedded SQL queries. Includes syntax error fallback.
- TypeScript/JavaScript (`TypeScriptParser`): Pure-Python extraction of interfaces, types, classes, methods, functions, arrow functions, imports, exports, client HTTP calls (`fetch`, `axios`), and cyclomatic complexity.
- SQL (`SqlParser`): Multi-dialect AST parsing via `sqlglot` for Oracle, Postgres, and ANSI; identifies tables, queries, and statement types.
- Shell (`ShellParser`): Tokenizes shell scripts via `shlex`, identifies pipelines, environment variable assignments/reads, and executed script targets (`RUNS_SCRIPT`).
- Config (`JsonConfigParser`, `YamlConfigParser`): Flattens nested JSON/YAML objects into dot-notated keypaths.

### Non-Responsibilities
- Does NOT resolve cross-file targets (e.g. mapping an import name to another file's symbol ID).
- Does NOT invoke LLMs or generate natural language summaries.
- Does NOT mutate global state or write to disk.

### Key Symbols
- `BaseParser`, `ParseResult` in [`base.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/base.py)
- `PythonParser` in [`python.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/python.py)
- `TypeScriptParser` in [`typescript.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/typescript.py)
- `SqlParser` in [`sql.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/sql.py)
- `ShellParser` in [`shell.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/shell.py)
- `JsonConfigParser`, `YamlConfigParser` in [`config.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/config.py)

---

## 3. Graph Builder and Symbol Resolver (`repopeek.graph`)

### Purpose
Aggregates parsed results into the canonical property graph, resolves cross-file references, computes mathematical blast radius, and projects specialized sub-graph lenses.

### Responsibilities
- `GraphBuilder`: Ingests `ParseResult` items, assigns git provenance, builds `CanonicalGraph`, converts to NetworkX (`to_networkx()`), validates structural integrity, and executes single-file incremental updates (`update_file()`).
- `SymbolResolver`: Builds multi-level index maps (`file_nodes`, `module_to_file`, `symbols_by_qualname`, `tables_by_name`, `configs_by_key`, `env_vars`) and resolves raw targets to concrete node IDs.
- `compute_blast_radius()`: Executes mathematical multi-hop traversal, calculates path decay and combined confidence, and classifies nodes into `direct`, `indirect`, and `excluded`.
- `project_lens()`: Filters the graph into 9 specialized functional lenses.

### Non-Responsibilities
- Does NOT perform lexical full-text search (delegated to SQLite FTS5).
- Does NOT format user-facing context packages (delegated to `ContextCompiler`).
- Does NOT make network calls.

### Key Symbols
- `GraphBuilder` in [`builder.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/graph/builder.py)
- `SymbolResolver` in [`resolver.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/graph/resolver.py)
- `compute_blast_radius()`, `BlastRadiusReport` in [`blast_radius.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/graph/blast_radius.py)
- `get_module_lens()`, `get_call_lens()`, `get_data_lens()`, etc. in [`lenses.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/graph/lenses.py)

---

## 4. Semantic Enrichment and Anti-Hallucination Guard (`repopeek.enrichment`)

### Purpose
Orchestrates bottom-up story generation across graph nodes while enforcing the 5-tier cost cascade and verifying generated claims.

### Responsibilities
- Top-down topological partition: Methods & functions -> classes -> modules -> others.
- 5-tier cascade:
  1. Trivial node filter (complexity == 1, 0 calls/reads/writes).
  2. SHA-256 content-hash cache.
  3. Cost governor / offline fallback pre-check.
  4. Hierarchical LLM summarization.
  5. `FactVerifier` validation.
- `FactVerifier`: Rejects stories that hallucinate database tables not in AST facts, claim external calls when `calls == 0`, or dump raw markdown code blocks.
- Falls back to `DeterministicStoryBuilder` whenever validation fails or offline mode is active.

### Non-Responsibilities
- Does NOT alter AST code facts (`facts: NodeFacts`).
- Does NOT create or delete graph nodes or edges.

### Key Symbols
- `StoryPipeline` in [`pipeline.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/enrichment/pipeline.py)
- `HierarchicalStoryGenerator` in [`summarizer.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/enrichment/summarizer.py)
- `FactVerifier` in [`verifier.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/enrichment/verifier.py)
- `DeterministicStoryBuilder` in [`templates.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/enrichment/templates.py)
- `StoryCache` in [`cache.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/enrichment/cache.py)
- `CostGovernor` in [`governor.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/enrichment/governor.py)

---

## 5. Hybrid Retrieval and Intent Engine (`repopeek.retrieval`)

### Purpose
Resolves high-level, natural language engineering tasks into concrete, ranked candidate symbols completely offline.

### Responsibilities
- Natural language normalization: Tokenizes query, filters operational stop words, separates action verbs from domain concepts, and stems technical terms.
- Code identifier extraction: Extracts dotted paths, camelCase tokens, snake_case tokens, and constants.
- Compound variant generation: Joins adjacent tokens into code-style identifiers.
- Negative constraint parsing: Extracts negation clauses (`without modifying shipping`, `do not touch X`).
- 6-component scoring: Combines exact matches, identifier overlap, concept overlap, SQLite FTS5 BM25, path relevance, and kind preference.
- Explain mode: Formats deterministic score breakdown reports for debugging.

### Non-Responsibilities
- Does NOT use vector embeddings or external vector databases.
- Does NOT execute LLMs for intent classification.
- Does NOT perform graph reachability analysis (delegated to `blast_radius.py`).

### Key Symbols
- `extract_task_identifiers()`, `resolve_task_to_symbols()`, `explain_task()` in [`intent.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval/intent.py)
- `RetrievalScore`, `SymbolCandidate`, `TaskIntent` in [`intent.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval/intent.py)

---

## 6. Context Compiler and Change Planner (`repopeek.context`)

### Purpose
Assembles task-driven, minimal context packages and actionable, risk-assessed step-by-step change plans for AI coding agents.

### Responsibilities
- Progressive disclosure rendering:
  - Level 1: Brief (<400 tokens) - task, top entrypoints, direct blast radius, high-level plan.
  - Level 2: Standard (600-1000 tokens) - adds signatures, stories, indirect blast radius, multi-tier constraints.
  - Level 3: Full (1200-1800 tokens) - adds exact source code snippets for zero-file-read edits.
- Constraint extraction: Synthesizes structural parameter constraints, return constraints, exception contracts, and schema invariants.
- Change plan generation: Evaluates risk drivers (number of callers, database mutations, cross-language bridges) and compiles pre-checks, implementation steps, and post-checks.
- Token budget enforcement: Prunes lower-priority nodes to guarantee package stays within specified budget.

### Non-Responsibilities
- Does NOT execute or apply code edits.
- Does NOT run test suites directly.

### Key Symbols
- `ContextCompiler`, `ContextPackage`, `ConstraintSet`, `ChangePlan`, `ChangePlanStep` in [`compiler.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/context/compiler.py)

---

## 7. Storage and Indexing Subsystem (`repopeek.storage`)

### Purpose
Manages persistent disk serialization, content-addressed sharding, SQLite CTE indexing, and Obsidian vault exports.

### Responsibilities
- Crash-safe atomic persistence: Staged directory writing with `.tmp_build_<uuid>` and atomic directory renaming.
- Artifact creation: Generates `graph.json`, `manifest.json`, `lenses/*.json`, and `shards/*.json`.
- SQLite database cache: Creates `cache.db` with indexed `nodes`, `edges`, `metadata`, and virtual `nodes_fts` (FTS5) table.
- Incremental updates: Modifies individual shards and SQLite rows in <50ms without full rebuilds.
- Obsidian vault export: Produces categorized markdown notes with frontmatter, wikilinks, and Obsidian color groups.

### Non-Responsibilities
- Does NOT execute business logic or compute blast radius (provides the database for it).

### Key Symbols
- `save_canonical_graph()`, `load_canonical_graph()`, `update_file_shard()` in [`json_store.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/json_store.py)
- `build_sqlite_cache()`, `query_sqlite_impact()`, `query_fts5_bm25()`, `update_sqlite_file()` in [`sqlite_cache.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/sqlite_cache.py)
- `export_to_obsidian_vault()`, `read_obsidian_node()` in [`obsidian_exporter.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/obsidian_exporter.py)

---

## 8. Query Engine and MCP Serving (`repopeek.query`)

### Purpose
Provides the high-level API facade consumed by the CLI and external AI coding agents.

### Responsibilities
- `GraphQueryEngine`: Unified query router for `lookup()`, `impact()`, `data_trace()`, `context_pack()`, `resolve_task()`, `compile_context()`, `change_plan()`, `co_changes()`, `http_routes()`, and `extract_snippet()`.
- `RepoPeekMCPServer`: Stdio JSON-RPC MCP server exposing 10 agent intelligence tools:
  1. `repopeek_context`
  2. `repopeek_plan`
  3. `repopeek_impact`
  4. `repopeek_routes`
  5. `repopeek_co_changes`
  6. `repopeek_resolve`
  7. `repopeek_lookup`
  8. `repopeek_neighbors`
  9. `repopeek_data_trace`
  10. `repopeek_context_pack`

### Non-Responsibilities
- Does NOT implement custom protocol transports beyond stdio JSON-RPC.

### Key Symbols
- `GraphQueryEngine` in [`engine.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/engine.py)
- `RepoPeekMCPServer` in [`mcp_server.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/mcp_server.py)
- `ContextPack` in [`pack.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/pack.py)
