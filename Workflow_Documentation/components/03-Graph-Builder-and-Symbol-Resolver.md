# Component: Graph Builder, Symbol Resolver & Lenses

## 1. Overview
This subsystem assembles multi-language parse results into the unified `CanonicalGraph`, resolves raw string references into concrete node targets across files and languages, provides single-file incremental updates, and projects specialized sub-graph lenses.

- **Package:** `repopeek.graph`
- **Source Files:**
  - [`repopeek/graph/builder.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/graph/builder.py)
  - [`repopeek/graph/resolver.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/graph/resolver.py)
  - [`repopeek/graph/lenses.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/graph/lenses.py)
- **Primary Tests:**
  - [`tests/test_graph_builder_and_lenses.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_graph_builder_and_lenses.py)
  - [`tests/test_foundation.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_foundation.py)

---

## 2. GraphBuilder (`repopeek.graph.builder`)

### `build(parse_results, repo_commit, dirty, blob_shas) -> CanonicalGraph`
1. Instantiates `CanonicalGraph`.
2. Adds all parsed nodes and raw edges.
3. Attaches git provenance (HEAD commit SHA, blob SHA, tool version).
4. Invokes `SymbolResolver(nodes, edges).resolve()` to resolve cross-file targets.
5. Invokes `HttpBoundaryBridge().resolve_and_link()` to discover and link client HTTP calls to server endpoints.
6. Returns canonical property graph.

### `update_file(file_path, graph, repo_root) -> CanonicalGraph`
Executes incremental updates for a single modified file in <50ms:
1. Identifies and purges all old nodes originating from `file_path`.
2. Purges all edges touching the purged nodes.
3. Re-parses `file_path` with the corresponding language parser.
4. Adds new nodes to the graph.
5. Resolves local and cross-file edges with `SymbolResolver`.
6. Re-evaluates HTTP boundaries.
7. Sets `graph.dirty = True`.

---

## 3. SymbolResolver (`repopeek.graph.resolver`)

The `SymbolResolver` maps raw syntactic targets to qualified canonical node IDs.

### Multi-Level Indexing
During initialization, `SymbolResolver` builds indexed maps:
- `file_nodes`: Path -> file node ID.
- `module_to_file`: Dotted module notation (e.g. `src.billing.invoice`) -> file node ID.
- `symbols_by_qualname`: `(norm_rel_path, qualname)` -> node ID.
- `symbols_by_name`: Bare identifier -> `[node_id, ...]`.
- `tables_by_name`: Table name (lowercase) -> table node ID.
- `variables_by_qualname`: `(norm_rel_path, qualname)` -> variable node ID.
- `configs_by_key`: Configuration keypath (e.g. `database.dialect`) -> config node ID.
- `env_vars`: Environment variable name -> command/script node ID.
- `file_imports`: File path -> `{imported_alias: target_module}`.

### Resolution Hierarchy (`_resolve_symbol`)
When resolving a call or class inheritance:
1. **Local Scope:** Checks if symbol exists in the same source file. If found -> `Confidence.RESOLVED`.
2. **Explicit Import Scope:** Checks if symbol was imported in `src_file`. Resolves through relative paths (`./api`, `../utils`) or dotted module paths. If matched -> `Confidence.RESOLVED`.
3. **Global Repository Lookup:** If bare symbol is globally unique in the repository -> `Confidence.RESOLVED`. If multiple exist -> `Confidence.AMBIGUOUS`. If none exist -> `Confidence.EXTERNAL`.

### Data Access Resolution (`_resolve_data_access`)
Resolves `READS` and `WRITES` edges:
1. Database tables matching `tables_by_name`.
2. Config keys matching exact keypath in `configs_by_key`.
3. Variables in local function or class scope (`self.<attr>`, `cls.<attr>`).
4. Environment variables matching `env_vars`.
5. Short config keys.

---

## 4. Multi-Lens Projections (`repopeek.graph.lenses`)

RepoPeek provides 9 specialized sub-graphs projected from `CanonicalGraph`:

| Lens | Allowed Node Kinds | Allowed Edge Types | Primary Purpose |
|---|---|---|---|
| **Module** | `file`, `module` | `IMPORTS`, `RUNS_SCRIPT`, `CALLS` | High-level file-to-file architecture and module dependencies. |
| **Symbol** | `file`, `module`, `class`, `function`, `method` | `DEFINED_IN` | Structural code nesting and symbol containment tree. |
| **Call** | `function`, `method`, `command`, `class` | `CALLS` | Executable call graphs and invocation paths. |
| **Class** | `class`, `method` | `INHERITS`, `DEFINED_IN` | Object-oriented class hierarchies and inheritance trees. |
| **Data** | `variable`, `function`, `method`, `class` | `READS`, `WRITES`, `DEFINED_IN` | Variable definitions, mutations, reads, and data state flow. |
| **Data Entity** | `sql_table`, `sql_query`, `json_config`, `yaml_config`, `function`, `method` | `READS`, `WRITES`, `EMBEDS_SQL` | Database tables, SQL queries, and configuration entities. |
| **Config** | `json_config`, `yaml_config`, `file`, `shell_script` | `READS`, `WRITES`, `DEFINED_IN` | Configuration keys, env vars, and code readers/writers. |
| **Process** | `file`, `shell_script`, `command` | `RUNS_SCRIPT`, `DEFINED_IN`, `READS`, `WRITES` | Shell script pipelines, batch jobs, and command executions. |
| **Bridges** | All kinds involved in cross-language edges | `EMBEDS_SQL`, `RUNS_SCRIPT`, `INVOKES`, cross-language `READS`/`WRITES` | Fullstack boundaries between Python, TypeScript, SQL, Shell, and Config. |
