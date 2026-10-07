# Component: MCP Server & Interactive Web Viewer

## 1. Overview
RepoPeek provides two consumer-facing interfaces:
1. **Model Context Protocol (MCP) Server:** A stdio JSON-RPC server exposing 10 agent intelligence tools for autonomous AI IDEs (Antigravity, Cursor, Claude Desktop).
2. **Interactive Web Graph Viewer:** A local, zero-dependency browser-based force-directed property graph explorer with 9 switchable lenses.

- **Packages:** `repopeek.query`, `repopeek.viewer`
- **Source Files:**
  - [`repopeek/query/mcp_server.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/mcp_server.py)
  - [`repopeek/viewer/server.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/viewer/server.py)
  - [`repopeek/viewer/index.html`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/viewer/index.html)
- **Primary Tests:**
  - [`tests/test_mcp_suite.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_mcp_suite.py)
  - [`tests/test_viewer_and_obsidian.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_viewer_and_obsidian.py)

---

## 2. MCP Server Specification (`RepoPeekMCPServer`)

Communicates over `sys.stdin` and `sys.stdout` following the 2024-11-05 Model Context Protocol JSON-RPC specification.

### 10 Registered Tools

| Tool Name | Parameters | Description |
|---|---|---|
| `repopeek_context` | `task` (str), `budget` (int, default 1500), `level` (int, 1-3), `format` ("markdown" / "json") | Compiles natural language task into minimal ContextPackage with progressive disclosure, constraints, and blast radius. |
| `repopeek_plan` | `task` (str) | Generates a 3-phase engineering change plan with risk drivers, pre-checks, actionable steps, and post-checks. |
| `repopeek_impact` | `target` (str), `max_depth` (int, default 5), `direction` ("both" / "upstream" / "downstream"), `threshold` (float, default 0.20) | Calculates multi-hop mathematical blast radius partitioned into direct, indirect, and excluded nodes. |
| `repopeek_routes` | *(None)* | Discovers all server route endpoints, client API calls (`fetch`/`axios`), and fullstack cross-language linkages. |
| `repopeek_co_changes` | `target` (str) | Queries historical git commit co-change patterns, conditional probabilities $P(B \mid A)$, and temporal coupling. |
| `repopeek_resolve` | `task` (str) | Resolves natural language engineering tasks to ranked candidate symbols via AST + SQLite FTS5 BM25 + RRF. |
| `repopeek_lookup` | `query` (str), `include_snippet` (bool, default False) | Retrieves atomic node card (<80 tokens) with optional physical source code span slice. |
| `repopeek_neighbors` | `node_id` (str), `direction` ("both" / "incoming" / "outgoing") | Inspects direct 1-hop relational graph edges. |
| `repopeek_data_trace` | `entity` (str) | Traces variable def-use and data entity flows (readers vs writers) across language boundaries. |
| `repopeek_context_pack` | `targets` (list[str]), `token_budget` (int, default 1500), `include_snippet` (bool) | Generates minimal sufficient context pack (<500 tokens) for safe target modifications. |

---

## 3. Interactive Web Graph Viewer (`repopeek.viewer`)

Launched via `python -m repopeek.cli --view [--port 8765]`:
- Uses standard library `http.server.ThreadingHTTPServer`.
- Serves [`repopeek/viewer/index.html`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/viewer/index.html) (29 KB single-file HTML5/JS zero-dependency client).

### REST Endpoints
- `GET /` or `GET /index.html`: Serves web viewer UI.
- `GET /api/graph?lens=<lens_name>`: Returns serialized node and edge arrays for the chosen lens (`call`, `module`, `data`, `data_entity`, `config`, `process`, `bridges`, `class`, `symbol`, or `all`).
- `GET /api/impact?target=<node_id>&depth=<max_depth>`: Returns blast radius report.
- `GET /api/pack?target=<node_id>`: Returns formatted markdown context pack.

### Web UI Features
- Force-directed physics layout with interactive pan and zoom.
- Node drawer: Click any node to inspect kind, file span, cyclomatic complexity, AST facts, and verified story narrative.
- One-click blast radius: Highlights upstream callers and downstream dependencies in glowing color accents while dimming unaffected nodes.
- Real-time search filter: Live filtering of symbols by substring or qualified name.
