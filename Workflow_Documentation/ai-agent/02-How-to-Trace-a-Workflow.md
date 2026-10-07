# How to Trace a Workflow

This document provides a concrete guide for tracing any request, query, or data transformation across RepoPeek from trigger to result.

---

## 1. Tracing Methodology

To understand how any feature works under the hood, trace it in 5 steps:

```text
1. Locate Trigger in Entry Point (CLI flag or MCP tool)
       ↓
2. Follow Delegation to Engine / Service Class
       ↓
3. Trace Graph Traversal or Model Transformations
       ↓
4. Inspect Persistence or External Transport
       ↓
5. Locate the Corresponding Unit Test in tests/
```

---

## 2. Concrete Example: Tracing `repopeek_context`

Suppose an agent wants to understand how natural language context packaging works:

### Step 1: Locate the Trigger
Open [repopeek/query/mcp_server.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/mcp_server.py) and search for `name == "repopeek_context"`.
- Finds the handler:
  ```python
  task = arguments["task"]
  level = arguments.get("level", 2)
  budget = arguments.get("budget", 1500)
  result = context_compiler.compile(task, level=level, budget_tokens=budget)
  ```

### Step 2: Follow Delegation to `ContextCompiler`
Navigate to [repopeek/retrieval/context_compiler.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval/context_compiler.py):
- Method: `ContextCompiler.compile(task, level, budget_tokens)`:
  - Line 45: Calls `self.retrieval_engine.retrieve(task, top_k=5)` to discover seed nodes.
  - Line 58: Calls `self.blast_engine.compute_blast_radius(seed_ids)` to identify impacted nodes and 5 risk tiers.
  - Line 75: Calls `self._extract_constraints(tiered_nodes)` to find database schema locks or protected components.
  - Line 95: Packs tiered nodes into `ContextPackage` obeying `budget_tokens`.
  - Line 120: Calls `self._generate_change_plan()` to output ordered edit steps.

### Step 3: Trace Sub-Engine Calls
- **Seed Retrieval:** Follow `self.retrieval_engine.retrieve()` to [repopeek/retrieval/engine.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval/engine.py#L32), which runs Channel 1 (Code Token Match) and Channel 2 (BM25 FTS5 Match) merged via RRF.
- **Blast Radius:** Follow `self.blast_engine.compute_blast_radius()` to [repopeek/analysis/blast_radius.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/analysis/blast_radius.py#L40), which runs BFS with Noisy-OR probability combination.

### Step 4: Trace Return Output
- `ContextPackage` model dumped to JSON or formatted as Markdown via `package.to_markdown()`.
- Returned via MCP JSON-RPC frame to standard output.

### Step 5: Locate Verification Tests
- Check [tests/test_context_compiler.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_context_compiler.py) and [tests/test_mcp_suite.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_mcp_suite.py).

---

## 3. Quick Lookup Table for Common Tracing Targets

| To Trace... | Start At | Engine Method | Test File |
|---|---|---|---|
| **File Indexing** | [repopeek/cli.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/cli.py#L220) | `GraphBuilder.build_from_directory()` | `test_graph_builder_and_lenses.py` |
| **Incremental Sync** | [repopeek/watcher/daemon.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/watcher/daemon.py#L30) | `IncrementalWatchDaemon._sync_file()` | `test_watch_daemon.py` |
| **HTTP Bridge** | [repopeek/bridges/http.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/bridges/http.py#L25) | `HTTPBridge.connect_endpoints()` | `test_http_bridge.py` |
| **Co-Change Mining**| [repopeek/temporal/miner.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/temporal/miner.py#L35) | `GitTemporalMiner.mine()` | `test_temporal_cochange.py` |
| **Obsidian Vault** | [repopeek/storage/obsidian_exporter.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/obsidian_exporter.py#L75) | `export_to_obsidian_vault()` | `test_viewer_and_obsidian.py` |
| **Web Viewer** | [repopeek/viewer/server.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/viewer/server.py#L25) | `GraphViewerHandler.do_GET()` | `test_viewer_and_obsidian.py` |
