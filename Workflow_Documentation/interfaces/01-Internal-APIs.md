# Internal Python APIs

This document details the public Python API surface of RepoPeek, designed for programmatic integration by developer tools, scripts, and embedded test harnesses.

---

## 1. GraphBuilder ([repopeek/graph/builder.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/graph/builder.py))

`GraphBuilder` coordinates repository crawling, multi-language AST parsing, cross-language HTTP bridging, and symbol resolution into a unified graph.

### `__init__(repo_root: Path, config: Optional[RepopeekConfig] = None)`
- **Parameters:**
  - `repo_root`: Absolute path to the repository root directory.
  - `config`: Optional configuration overrides.
- **Invariants:** Creates an internal NetworkX `DiGraph` and sets up qualified name registries.

### `build_from_directory() -> CanonicalGraph`
- **Returns:** Fully populated [CanonicalGraph](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py#L131) with resolved AST, inheritance, and HTTP bridge edges.
- **Exceptions:** `FileNotFoundError` if `repo_root` does not exist.

### `update_file(rel_path: str) -> bool`
- **Parameters:** `rel_path` - POSIX relative path to the modified file.
- **Description:** Performs an incremental graph update in `<50ms` by pruning existing nodes/edges belonging to that file, re-parsing, and reconnecting edges.
- **Returns:** `True` if successfully updated, `False` if file was removed or parsing failed.

---

## 2. GraphQueryEngine ([repopeek/query/engine.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/engine.py))

`GraphQueryEngine` provides read-only traversal, symbol lookup, dependency analysis, and impact assessment.

### `lookup(query: str) -> List[NodeCard]`
- **Parameters:** `query` - Qualified ID (e.g. `src/main.py::handle_request`) or short symbol name (`handle_request`).
- **Returns:** List of matching [NodeCard](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py#L76) instances.

### `get_neighbors(node_id: str, direction: str = "both", edge_types: Optional[List[EdgeType]] = None) -> List[Tuple[Edge, NodeCard]]`
- **Parameters:**
  - `node_id`: Target node identifier.
  - `direction`: `"incoming"`, `"outgoing"`, or `"both"`.
  - `edge_types`: Optional filter for specific edge types (`EdgeType.CALLS`, `EdgeType.INVOKES`, etc.).
- **Returns:** List of `(Edge, NodeCard)` pairs connected to the target.

### `get_blast_radius(node_id: str, max_depth: int = 3, min_risk: float = 0.05) -> BlastRadiusResult`
- **Parameters:**
  - `node_id`: Seed node being changed.
  - `max_depth`: Maximum traversal hops (default: 3).
  - `min_risk`: Minimum cumulative probability threshold for inclusion (default: 0.05).
- **Returns:** `BlastRadiusResult` containing impacted nodes, risk scores, and 5-tier classification.

### `trace_data_flow(entity_id: str) -> Dict[str, List[NodeCard]]`
- **Parameters:** `entity_id` - Variable, parameter, or database table node ID.
- **Returns:** Dictionary with keys `"producers"` (nodes with `WRITES_TO`) and `"consumers"` (nodes with `READS_FROM`).

---

## 3. ContextCompiler ([repopeek/retrieval/context_compiler.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval/context_compiler.py))

`ContextCompiler` takes a developer prompt or bug description, identifies candidate seeds, computes dependencies, and compiles a budget-governed context package.

### `compile(task: str, level: int = 2, budget_tokens: int = 1500) -> ContextPackage`
- **Parameters:**
  - `task`: Natural language task description (e.g., `"Update auth session timeout in Redis"`).
  - `level`: Progressive disclosure detail level (`1`: brief summaries, `2`: standard contracts + blast radius, `3`: full code spans).
  - `budget_tokens`: Token constraint for the compiled package (default: 1500).
- **Returns:** [ContextPackage](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py#L224) with target nodes, blast radius, constraints, and formatted Markdown context.

### `generate_plan(task: str, context_pack: Optional[ContextPackage] = None) -> ChangePlan`
- **Parameters:**
  - `task`: Task description.
  - `context_pack`: Pre-compiled context package (or `None` to compile automatically).
- **Returns:** [ChangePlan](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py#L254) containing sequential edit steps, target files, risk assessments, and test validation commands.

---

## 4. HybridRetrievalEngine ([repopeek/retrieval/engine.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval/engine.py))

Combines AST token matching with BM25 natural language search using Reciprocal Rank Fusion.

### `retrieve(task: str, top_k: int = 10) -> List[RetrievalScore]`
- **Parameters:**
  - `task`: Raw query string.
  - `top_k`: Number of candidate symbols to return.
- **Returns:** Ranked list of `RetrievalScore` items with normalized scores, match sources, and matched terms.

### `explain(task: str) -> Dict[str, Any]`
- **Returns:** Diagnostic diagnostic breakdown including normalized tokens, candidate counts from Channel 1 (Code Token Match) and Channel 2 (BM25 FTS5), and intermediate fusion ranks.

---

## 5. GitTemporalMiner ([repopeek/temporal/miner.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/temporal/miner.py))

Extracts multi-commit historical co-change patterns to uncover hidden dependencies.

### `mine(max_commits: int = 1000, half_life_days: float = 90.0) -> Dict[Tuple[str, str], float]`
- **Parameters:**
  - `max_commits`: Maximum git commit history depth to scan.
  - `half_life_days`: Decay parameter for time-weighted commit relevance.
- **Returns:** Mapping of `(file_a, file_b)` pairs to conditional co-change probabilities $P(B \mid A) \in [0.0, 1.0]$.

### `synthesize_edges(graph: CanonicalGraph, threshold: float = 0.3) -> int`
- **Parameters:**
  - `graph`: Canonical graph to enrich.
  - `threshold`: Minimum co-change probability required to insert an edge.
- **Returns:** Count of `CO_CHANGED_WITH` edges added to the graph.

---

## 6. Storage Persistence Functions ([repopeek/storage/json_store.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/json_store.py))

### `save_canonical_graph(graph: CanonicalGraph, output_dir: Path, materialize_lenses: bool = True) -> Dict[str, Any]`
- **Description:** Atomically persists the graph into `graph.json`, `lenses/`, `shards/`, and `manifest.json`.
- **Returns:** Parsed manifest dictionary with generated checksums.

### `load_canonical_graph(storage_dir: Path) -> CanonicalGraph`
- **Description:** Loads the complete graph from `.repopeek/graph.json`.
- **Exceptions:** `FileNotFoundError` if the directory or `graph.json` is missing.
