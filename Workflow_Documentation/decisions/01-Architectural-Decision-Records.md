# Architectural Decision Records (ADR)

This document records the foundational architectural decisions made across the lifecycle of RepoPeek, detailing the problem context, chosen solution, trade-offs, and rejected alternatives based on codebase evidence.

---

## ADR-001: In-Memory NetworkX Graph vs External Graph Databases

- **Status:** Accepted and Active.
- **Context:** RepoPeek constructs multi-language code property graphs with up to tens of thousands of nodes and edges representing modules, classes, functions, calls, and database tables.
- **Decision:** Use an in-memory NetworkX `DiGraph` wrapped inside a Pydantic [CanonicalGraph](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py#L131) model.
- **Why Chosen:**
  - Zero external database services (Neo4j, Memgraph, ArangoDB) to install, run, or authenticate.
  - Trivial installation via `pip install .` on any developer laptop or CI container.
  - High-performance BFS/DFS traversal and topological sorting in pure Python.
- **Alternatives Considered:**
  - *Neo4j / Memgraph:* Rejected due to heavy runtime overhead, container dependencies, and operational friction for single-developer and agent workflows.
  - *Raw Adjacency Lists:* Rejected because NetworkX provides mature, thoroughly tested cycle detection and path-finding algorithms out of the box.
- **Trade-offs:** In-memory footprint scales linearly with codebase size (approx. 50–100MB for a 100k-line project). Memory caps prevent indexing repositories with millions of AST nodes on constrained machines.

---

## ADR-002: Deterministic Sharded JSON with Atomic Swap Persistence

- **Status:** Accepted and Active.
- **Context:** The persisted graph must be readable by multiple concurrent processes (CLI, MCP server, web viewer), safe against abrupt crashes, and inspectable by humans.
- **Decision:** Persist graph data as deterministic JSON files (`graph.json`, `lenses/*.json`, `shards/*.json`, `manifest.json`) using sorted keys, two-space indentation, and atomic directory rename (`.tmp_build_<uuid>` $\to$ `.repopeek/`).
- **Why Chosen:**
  - **Zero Read Corruption:** Readers never encounter half-written files during active indexing passes.
  - **Deterministic Checksums:** Byte-identical source code yields byte-identical SHA-256 graph hashes, enabling robust cache invalidation.
  - **Progressive Loading:** Tools needing only module-level structure can load `lenses/module.json` without parsing the monolithic `graph.json`.
- **Alternatives Considered:**
  - *Pickle / Binary Serialization:* Rejected due to security risks (arbitrary code execution) and lack of human readability.
  - *Single Monolithic JSON File:* Rejected because large repositories require incremental loading of single-file subgraphs.
- **Trade-offs:** JSON serialization has higher CPU and disk footprint than binary formats, but offers universal tool interoperability.

---

## ADR-003: Derived SQLite Traversal Cache with FTS5

- **Status:** Accepted and Active.
- **Context:** While JSON is ideal for interchange and archival, multi-hop recursive graph traversals and fuzzy text queries require indexing for sub-second agent responsiveness.
- **Decision:** Generate an optional/derived SQLite database (`.repopeek/cache.db`) featuring indexes on `(src, type)` and `(dst, type)`, combined with an FTS5 full-text virtual table (`nodes_fts`).
- **Why Chosen:**
  - Uses Python's built-in `sqlite3` module (zero external dependencies).
  - Common Table Expressions (Recursive CTEs) enable deep multi-hop blast radius queries in `<2ms`.
  - FTS5 enables BM25 keyword matching for natural language intent resolution.
  - Strictly derived: If `cache.db` corrupts, it can be regenerated immediately from `graph.json`.
- **Alternatives Considered:**
  - *Elasticsearch / Meilisearch:* Rejected due to operational complexity and external service requirements.
- **Trade-offs:** Writing the SQLite database adds ~5–10% overhead to full indexing runs, but yields a $10\times$ query speedup.

---

## ADR-004: Pure-Python Regex AST State Machine for TypeScript / JavaScript

- **Status:** Accepted and Active.
- **Context:** RepoPeek must parse modern TypeScript, TSX, and JavaScript to build full-stack code graphs.
- **Decision:** Implement a pure-Python regex-based AST extractor in [repopeek/parsers/typescript.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/typescript.py) capable of extracting classes, methods, functions, imports, interfaces, type aliases, and fetch calls.
- **Why Chosen:**
  - Eliminates Node.js, `npm`, or Node subprocess dependencies from Python environments.
  - Avoids native C/Rust binary extension compilation issues associated with `tree-sitter` on varied Windows and ARM environments.
- **Alternatives Considered:**
  - *Tree-sitter Python bindings:* Rejected due to platform-specific wheel compilation failures and C runtime dependencies.
  - *Spawning Node.js / Babel CLI:* Rejected due to high subprocess latency and requiring Node.js to be installed on developer systems.
- **Trade-offs:** Regex state machines cannot resolve complex TypeScript AST nuances like deeply nested ternary macros or conditional type resolution.

---

## ADR-005: 5-Tier Semantic Enrichment Fallback Cascade

- **Status:** Accepted and Active.
- **Context:** Semantic code graphs require natural language summaries, business contexts, and architectural invariants. Relying exclusively on external LLM APIs creates rate-limit failures, high costs, and breaks offline development.
- **Decision:** Implement a 5-tier fallback cascade in [repopeek/enrichment/](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/enrichment/):
  1. Cached `NodeStory` (hash match)
  2. AST Docstrings
  3. AST Invariants (purity, I/O side effects)
  4. Deterministic template heuristics
  5. Groq Cloud LLM API (`qwen/qwen3.8-27b`)
- **Why Chosen:**
  - Complete offline functionality (`--offline`).
  - Graceful degradation under network errors or HTTP 429 rate limits.
  - Zero token expenditure for unchanged files.
- **Trade-offs:** Heuristic stories provide less nuanced business explanations than frontier LLMs, but guarantee 100% pipeline reliability.

---

## ADR-006: Hybrid Dual-Channel Retrieval with Reciprocal Rank Fusion (RRF)

- **Status:** Accepted and Active.
- **Context:** Developer tasks combine precise code identifiers (e.g. `verify_jwt_token`) with high-level conceptual goals (e.g. `increase session timeout`). Single retrieval approaches perform poorly on mixed queries.
- **Decision:** Implement parallel retrieval channels:
  - Channel 1: Code token matching (symbol names, qualified IDs, paths).
  - Channel 2: BM25 FTS5 full-text matching on natural language stories.
  - Merged via Reciprocal Rank Fusion: $\text{RRF}(d) = \sum_{c \in \{1, 2\}} \frac{1}{60 + \text{rank}_c(d)}$.
- **Why Chosen:**
  - Outperforms standalone BM25 or semantic embeddings on mixed code-and-prose queries.
  - Requires zero GPU or embedding model downloads.
- **Trade-offs:** Requires tuning the smoothing constant $k$ (empirically set to 60).

---

## ADR-007: Stdio JSON-RPC Model Context Protocol (MCP)

- **Status:** Accepted and Active.
- **Context:** Expose repository intelligence directly to autonomous coding agents (Claude Desktop, Cursor, Antigravity).
- **Decision:** Implement the Model Context Protocol over standard I/O (`repopeek --serve-mcp`) using JSON-RPC 2.0.
- **Why Chosen:**
  - Standardized protocol native to modern agentic coding environments.
  - Zero open network sockets or localhost port conflicts.
  - Process lifecycle automatically governed by the parent AI editor.
- **Trade-offs:** Stdio streams are sensitive to stray `print()` statements from dependencies, requiring strict redirection of diagnostics to `stderr`.
