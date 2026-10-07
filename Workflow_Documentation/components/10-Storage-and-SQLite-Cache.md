# Component: Storage, Sharding & SQLite Cache

## 1. Overview
The storage subsystem provides durable persistence, content-addressed sharding, atomic directory swapping, high-speed SQLite recursive CTE traversals, full-text BM25 search (FTS5), and native Obsidian vault exports.

- **Package:** `repopeek.storage`
- **Source Files:**
  - [`repopeek/storage/json_store.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/json_store.py)
  - [`repopeek/storage/sqlite_cache.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/sqlite_cache.py)
  - [`repopeek/storage/obsidian_exporter.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/obsidian_exporter.py)
  - [`repopeek/storage/provenance.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/provenance.py)
- **Primary Tests:**
  - [`tests/test_graph_persistence.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_graph_persistence.py)
  - [`tests/test_viewer_and_obsidian.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_viewer_and_obsidian.py)

---

## 2. Deterministic JSON Sharding & Atomic Swap

In [`json_store.py:save_canonical_graph`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/json_store.py#L78):
1. **Crash-Safe Staging:** Writes all artifacts to `.tmp_build_<uuid12>`.
2. **Deterministic Formatting:** Uses `dump_deterministic_json()` with `sort_keys=True, indent=2, ensure_ascii=False` and standardizes line breaks to `\n`.
3. **Artifact Manifest (`manifest.json`):**
   - Records SHA-256 hash for `graph.json`, each of the 9 `lenses/*.json`, and every source file shard in `shards/*.json`.
   - Records repository commit SHA, dirty state, and total node/edge counts.
4. **Atomic Rename Swap:**
   - On Linux/macOS: Atomic directory swap.
   - On Windows: Existing directory is renamed to `.tmp_old_<uuid>`, staging directory renamed to destination, and old directory removed.

---

## 3. SQLite Traversal Cache (`cache.db`)

In [`sqlite_cache.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/sqlite_cache.py):

### Database Schema
```sql
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    sig TEXT,
    file TEXT,
    start_line INTEGER,
    end_line INTEGER,
    complexity INTEGER,
    facts_json TEXT,
    story_json TEXT,
    content_hash TEXT NOT NULL
);

CREATE TABLE edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    type TEXT NOT NULL,
    confidence TEXT NOT NULL,
    how_derived TEXT
);

CREATE INDEX idx_edges_src ON edges(src, type);
CREATE INDEX idx_edges_dst ON edges(dst, type);
CREATE INDEX idx_nodes_kind ON nodes(kind);
CREATE INDEX idx_nodes_file ON nodes(file);

CREATE VIRTUAL TABLE nodes_fts USING fts5(
    node_id,
    qualified_name,
    symbol_name,
    sig,
    file_path,
    story_text,
    tokenize='unicode61'
);
```

### Recursive Common Table Expression (CTE) Traversal
Computes upstream blast radius in a single native SQLite query:
```sql
WITH RECURSIVE impact_tree(src, dst, type, depth) AS (
    SELECT src, dst, type, 1
    FROM edges
    WHERE dst = ?
    UNION
    SELECT e.src, e.dst, e.type, it.depth + 1
    FROM edges e
    JOIN impact_tree it ON e.dst = it.src
    WHERE it.depth < ?
)
SELECT DISTINCT it.src, it.dst, it.type, it.depth, n.kind, n.file
FROM impact_tree it
LEFT JOIN nodes n ON it.src = n.id
ORDER BY it.depth ASC;
```

### SQLite FTS5 Full-Text Search
`query_fts5_bm25(db_path, query, limit=50)` queries the virtual table:
- Weights columns: `qualified_name=5.0, symbol_name=5.0, sig=4.0, file_path=2.5, story_text=1.5`.
- Returns `List[Tuple[node_id, bm25_score]]` in under 2 milliseconds.

---

## 4. Native Obsidian Vault Exporter (`obsidian_exporter.py`)

Exports the canonical graph as an Obsidian vault:
- `.obsidian/app.json`: Configures Live Preview and shortest link format.
- `.obsidian/graph.json`: Configures native force-directed graph color groups:
  - `path:Modules`: Blue (`#6D9EEB`)
  - `path:Classes`: Orange (`#E69138`)
  - `path:Functions`: Green (`#7BB87B`)
  - `path:Entities`: Red/Salmon (`#FF9900`)
  - `path:Configs`: Purple (`#FF6666`)
- `00 Overview.md`: Root dashboard note with repository stats and wikilinks.
- Notes contain YAML frontmatter (`id`, `kind`, `file`, `span`, `complexity`, `confidence`) and bidirectional wikilinks (`[[Function_Name]]`).
- Supports opening directly via Obsidian Desktop URI: `obsidian://open?vault=<name>`.
