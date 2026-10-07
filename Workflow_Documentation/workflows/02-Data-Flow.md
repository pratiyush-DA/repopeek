# Data Flow Specification

## 1. Overview of Data Flow

Data in RepoPeek moves strictly forward from raw source files on disk through structured AST models, canonical graph representations, enriched narrative overlays, persistent disk caches, and finally into task-specific context packages.

```text
Filesystem (.py, .ts, .sql, .sh, .json, .yaml)
     │
     ▼
DiscoveredFile
     │  (Validated by classifier & hasher)
     ▼
ParseResult (Nodes & Edges)
     │  (Constructed by language parsers)
     ▼
CanonicalGraph
     │  (Resolved by SymbolResolver, HttpBoundaryBridge, GitTemporalMiner)
     ▼
Enriched CanonicalGraph
     │  (Enriched with NodeStory via 5-tier cascade & FactVerifier)
     ├───► output/graph.json (Deterministic JSON)
     ├───► output/lenses/*.json (9 specialized projections)
     ├───► output/shards/*.json (Source file shards)
     └───► output/cache.db (SQLite nodes, edges, FTS5)
               │
               ▼
Task Query / Natural Language Intent
     │
     ▼
TaskIntent (Identifiers, concepts, stems, exclusions)
     │
     ▼
SymbolCandidate Pool (Scored via AST + FTS5 BM25 + RRF)
     │
     ▼
BlastRadiusReport (Partitioned into direct, indirect, excluded)
     │
     ▼
ContextPackage (Budgeted Markdown: Level 1, 2, or 3) + ChangePlan
```

---

## 2. Detailed Object Lifecycle and Transformations

### A. `DiscoveredFile`
- **Created By:** `discover_repository()` in [`crawler.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/crawler.py).
- **Validation:** Skips binary files (`is_binary_file`), skips files > `max_file_size_kb`, filters by `IgnoreRuleSet`.
- **Fields:**
  - `path`: Absolute filesystem path.
  - `rel_path`: Normalized POSIX path relative to repo root (e.g. `src/billing/invoice.py`).
  - `file_type`: Classified `FileType` enum.
  - `size_bytes`: Integer size.
  - `sha256`: SHA-256 hex digest of file contents.
  - `blob_sha`: Git blob SHA (`git hash-object`).
  - `parse_status`: Status enum (`pending`, `ok`, `error`, `skipped_size`, etc.).
- **Transformed Into:** Passed to appropriate `BaseParser.parse_file()`.

---

### B. `NodeCard`
- **Created By:** `PythonParser`, `TypeScriptParser`, `SqlParser`, `ShellParser`, `JsonConfigParser`, `YamlConfigParser`.
- **Schema:** Defined in [`schema.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py).
- **ID Convention:** Standard stable URI format:
  $$\text{id} = \text{lang} : \text{repo\_rel\_path} :: \text{qualified\_symbol\_name}$$
  *Example:* `py:src/billing/invoice.py::InvoiceParser.parse`
- **Component Sub-Structures:**
  - `kind`: `file`, `module`, `class`, `function`, `method`, `sql_table`, `sql_query`, `json_config`, `yaml_config`, `shell_script`, `command`, `variable`.
  - `sig`: Exact call signature, method declaration, or config line.
  - `span`: `Span(file="src/billing/invoice.py", start=14, end=35)`.
  - `facts`: `NodeFacts(calls=2, reads=["invoices"], writes=[], raises=["ParseError"], complexity=3, params=["payload: bytes"], returns="Invoice")`.
  - `story`: Populated during Layer 2 semantic enrichment:
    `NodeStory(text="Parses raw invoice payload bytes into validated Invoice entity", source="deterministic", confidence="high")`.
  - `snippet`: Source code slice extracted on-demand for Level 3 context packs.
  - `content_hash`: SHA-256 of normalized body or file content.
  - `provenance`: `NodeProvenance(commit="a1b2c3d...", tool_version="0.1.0", blob_sha="e5f6...")`.

---

### C. `Edge`
- **Created By:** Parsers (local edges), `SymbolResolver` (cross-file edges), `HttpBoundaryBridge` (cross-language edges), `GitTemporalMiner` (co-change edges).
- **Schema:** Defined in [`schema.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py).
- **Fields:**
  - `src`: Source `NodeCard.id`.
  - `dst`: Target `NodeCard.id`.
  - `type`: `EdgeType` enum:
    - `DEFINED_IN`: Structural containment (method in class, class in file).
    - `CALLS`: Method / function invocation.
    - `IMPORTS`: Module import dependency.
    - `READS`: Variable, table, or config attribute read.
    - `WRITES`: Variable, table, or config mutation.
    - `INHERITS`: Class inheritance.
    - `IMPLEMENTS`: Interface implementation.
    - `INVOKES`: Cross-language HTTP boundary call (client -> server route).
    - `RAISES`: Exception raised by function.
    - `CATCHES`: Exception handled in try-except block.
    - `TESTS_CODE`: Association between test function and target under test.
    - `EMBEDS_SQL`: Python/Shell code embedding an inline SQL statement.
    - `RUNS_SCRIPT`: Shell command executing a script file.
    - `CO_CHANGED_WITH`: Historical commit co-change temporal edge.
  - `confidence`: `Confidence` enum (`resolved`, `ambiguous`, `dynamic`, `external`, `unresolved`).
  - `evidence`: `Evidence(file, start_line, end_line, how_derived)`.

---

### D. `CanonicalGraph`
- **Created By:** `GraphBuilder.build()`.
- **Validation:** `GraphBuilder.validate_graph()` checks for dangling internal edges.
- **In-Memory Representation:**
  - `nodes`: `Dict[str, NodeCard]` (lookup by ID in $O(1)$).
  - `edges`: `List[Edge]`.
  - Adjacency caches: `_cached_adj = (incoming_edges, outgoing_edges)`.
- **Export Formats:**
  - NetworkX `MultiDiGraph`: Via `GraphBuilder.to_networkx()`.
  - Serialized Dictionary: Via `serialize_graph_to_dict()` with deterministic sorting.

---

### E. `TaskIntent`
- **Created By:** `extract_task_identifiers()` in [`intent.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval/intent.py).
- **Input:** Raw user prompt e.g. `"Fix ParseError in InvoiceParser.parse without modifying shipping"`.
- **Extracted Fields:**
  - `normalized`: Lowercased, punctuation-cleaned prompt.
  - `identifiers`: Explicit code tokens e.g. `["InvoiceParser.parse", "ParseError"]`.
  - `concepts`: Non-stop-word domain terms e.g. `["invoice", "parser", "parse", "error"]`.
  - `stemmed_concepts`: Suffix-normalized terms e.g. `["invoic", "parser", "pars", "error"]`.
  - `compounds`: Adjacent bigrams e.g. `["invoice_parser", "parser_parse"]`.
  - `exclusions`: Negative constraint targets e.g. `["shipping"]`.

---

### F. `ContextPackage`
- **Created By:** `ContextCompiler.compile()` in [`compiler.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/context/compiler.py).
- **Consumed By:** AI coding agents via CLI, MCP server, or API.
- **Fields:**
  - `task`: Original prompt.
  - `token_budget`: Cap (default 1500 tokens).
  - `estimated_tokens`: Computed tokens for rendered markdown.
  - `raw_file_tokens`: Equivalent tokens if all touched files were read in full.
  - `token_reduction_pct`: Measured savings (typically 90% - 98%).
  - `entrypoints`: Top ranked symbol candidate cards.
  - `direct`: Affected nodes in direct blast radius.
  - `indirect`: Affected nodes in indirect blast radius.
  - `excluded`: Nodes pruned due to negative constraints or low confidence.
  - `constraints`: `ConstraintSet(parameters, returns, exceptions, schema, invariants)`.
  - `change_plan`: Step-by-step risk-assessed `ChangePlan`.
  - `snippets`: Source code slices for Level 3 disclosure.
  - `affected_files`: Deduplicated file paths requiring review or modification.
