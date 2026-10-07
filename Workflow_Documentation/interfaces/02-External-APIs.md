# External APIs and Protocols

This document details all external interfaces exposed or consumed by RepoPeek: the Model Context Protocol (MCP) JSON-RPC suite, the Web Viewer HTTP REST endpoints, and the Groq LLM cloud API.

---

## 1. Model Context Protocol (MCP) Suite

RepoPeek provides a full-featured Model Context Protocol (MCP) stdio server in [repopeek/query/mcp_server.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/mcp_server.py). Coding agents communicate with RepoPeek via JSON-RPC 2.0 messages exchanged over standard input/output.

### 1.1 Tool Inventory

The server exposes **10 tools**:

| Tool Name | Purpose | Primary Inputs |
|---|---|---|
| `repopeek_lookup` | Retrieve node card metadata, facts, story, and span by query | `query: string`, `include_snippet: bool` |
| `repopeek_neighbors` | Inspect 1-hop inbound and outbound dependencies | `node_id: string`, `direction: string`, `edge_types: list[string]` |
| `repopeek_impact` | Compute multi-hop blast radius, risk scores, and tier breakdown | `node_id: string`, `max_depth: int`, `min_risk: float` |
| `repopeek_data_trace` | Trace data-flow def-use chains for variables/tables | `entity_id: string` |
| `repopeek_context_pack` | Assemble minimal context pack for specific targets | `targets: list[string]`, `budget_tokens: int` |
| `repopeek_context` | Compile task-driven context package with progressive disclosure | `task: string`, `level: int` (1-3), `budget: int` |
| `repopeek_plan` | Generate risk-assessed, step-by-step engineering change plan | `task: string` |
| `repopeek_routes` | Discover API endpoints, route handlers, and client fetch links | None |
| `repopeek_co_changes` | Query historical co-change probabilities and temporal neighbors | `target: string`, `min_probability: float` |
| `repopeek_resolve` | Map natural language task to candidate symbols via hybrid retrieval | `task: string`, `top_k: int` |

### 1.2 Tool Schemas (JSON-RPC)

#### Example: `repopeek_context`
```json
{
  "name": "repopeek_context",
  "description": "Compile task-driven context package with blast radius and constraints",
  "inputSchema": {
    "type": "object",
    "properties": {
      "task": {
        "type": "string",
        "description": "Natural language task or bug description"
      },
      "level": {
        "type": "integer",
        "description": "Progressive disclosure level (1: brief, 2: standard, 3: full)",
        "default": 2
      },
      "budget": {
        "type": "integer",
        "description": "Token budget cap for prompt injection",
        "default": 1500
      }
    },
    "required": ["task"]
  }
}
```

#### Example: `repopeek_impact`
```json
{
  "name": "repopeek_impact",
  "description": "Compute upstream blast radius for a node",
  "inputSchema": {
    "type": "object",
    "properties": {
      "node_id": {
        "type": "string",
        "description": "Target qualified node identifier"
      },
      "max_depth": {
        "type": "integer",
        "description": "Maximum traversal depth hops",
        "default": 3
      },
      "min_risk": {
        "type": "number",
        "description": "Minimum probability threshold",
        "default": 0.05
      }
    },
    "required": ["node_id"]
  }
}
```

---

## 2. Interactive Web Viewer REST API

The local web server in [repopeek/viewer/server.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/viewer/server.py) serves the HTML5 graph visualization UI and provides REST endpoints.

- **Host & Port:** `http://127.0.0.1:8765` (configurable via `--port`).
- **Transport:** HTTP/1.1 over TCP.
- **CORS:** `Access-Control-Allow-Origin: *` enabled on all responses.

### 2.1 Endpoints

#### `GET /` or `GET /index.html`
- **Response:** `200 OK`, `Content-Type: text/html; charset=utf-8`.
- **Payload:** Static single-page application rendering the Cytoscape/Vis.js interactive canvas.

#### `GET /api/graph?lens=<lens_name>`
- **Parameters:**
  - `lens` (optional): Name of pre-materialized lens (`call`, `module`, `symbol`, `class`, `data`, `data_entity`, `config`, `process`, `bridges`, or `all`).
- **Response:** `200 OK`, `Content-Type: application/json`.
- **Schema:**
  ```json
  {
    "nodes": [
      {
        "id": "src/main.py::app",
        "kind": "variable",
        "span": {"file": "src/main.py", "start": 10, "end": 10}
      }
    ],
    "edges": [
      {
        "src": "src/main.py::run",
        "dst": "src/main.py::app",
        "type": "USES"
      }
    ]
  }
  ```

#### `GET /api/impact?target=<node_id>&depth=<int>`
- **Parameters:**
  - `target` (required): Target node identifier.
  - `depth` (optional, default 5): Maximum traversal depth.
- **Response:** `200 OK`, `Content-Type: application/json`.
- **Schema:**
  ```json
  {
    "target": "src/auth.py::verify_token",
    "impacted_count": 8,
    "nodes": ["src/api/routes.py::login", "src/middleware/auth.py::auth_wrapper"],
    "edges": [
      {"src": "src/api/routes.py::login", "dst": "src/auth.py::verify_token", "type": "CALLS"}
    ]
  }
  ```

#### `GET /api/pack?target=<node_id>`
- **Parameters:**
  - `target` (required): Target symbol or identifier.
- **Response:** `200 OK`, `Content-Type: text/plain; charset=utf-8`.
- **Payload:** Formatted Markdown context pack for the target symbol.

---

## 3. Groq LLM Cloud API

RepoPeek integrates with Groq's high-speed inference API via [repopeek/llm/groq.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/llm/groq.py) during semantic enrichment passes.

### 3.1 Connection Specification
- **Base URL:** `https://api.groq.com/openai/v1`
- **Endpoint:** `/chat/completions`
- **Method:** `POST`
- **Authentication:** `Authorization: Bearer $GROQ_API_KEY`

### 3.2 Active Models
| Tier | Model Identifier | Purpose |
|---|---|---|
| **Fast / Balanced** | `qwen/qwen3.8-27b` | Primary enrichment engine for function summaries, invariants, and purpose generation |
| **Strong** | `openai/gpt-oss-120b` | Complex architecture summarization and edge-case verification |

### 3.3 Request / Response Contract
- **Request Format:** System prompt containing AST facts, code snippet, and strict JSON output schema.
- **Enforcement:** Structured output requested with `response_format={"type": "json_object"}`.
- **Client Parsing:** Responses are parsed directly into [NodeStory](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py#L58) instances.
- **Network Resilience:** Uses exponential backoff on HTTP 429 (rate-limit) and 503 (service unavailable) responses; falls back to offline mode on persistent errors.
