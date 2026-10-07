# How to Understand the Repository

This guide enables an incoming AI coding agent or senior engineer to build an accurate mental model of RepoPeek in under 5 minutes.

---

## 1. The Core Mental Model

At its simplest:

> **RepoPeek is a compiler that converts raw polyglot source code into a queryable semantic code property graph, computes mathematical blast radius, and compiles progressive context packages for LLM coding agents.**

```text
Filesystem Source Code (Python, TypeScript, SQL, Docker, YAML)
                     ↓
        AST & Heuristic Parsers
                     ↓
         Canonical Graph (NetworkX)
                     ↓
   Semantic Enrichment (AST Facts + LLM Stories)
                     ↓
  Storage Engine (Deterministic JSON + SQLite Cache)
                     ↓
        Dual-Channel Hybrid Retrieval
                     ↓
    Mathematical Blast Radius Propagation
                     ↓
       Progressive Context Compiler
                     ↓
       AI Agent Prompts & MCP Tools
```

---

## 2. The 3 Primary Entry Points

| Entry Point | Implementation | Purpose |
|---|---|---|
| **CLI** | [repopeek/cli.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/cli.py) | Human command-line interface, batch indexing, lookup, impact, and debugging. |
| **MCP Server** | [repopeek/query/mcp_server.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/mcp_server.py) | Stdio JSON-RPC 2.0 tool server for AI agents (Cursor, Claude Desktop, Antigravity). |
| **Web Viewer** | [repopeek/viewer/server.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/viewer/server.py) | Local HTTP server rendering interactive Cytoscape/Vis.js graph visualization. |

---

## 3. The Core Data Model

Before reading any processing logic, inspect [repopeek/models/schema.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py):
1. **[NodeCard](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py#L76):** A single code entity (function, class, module, database table, docker service). Key attributes: `id` (e.g. `src/main.py::run`), `kind`, `sig`, `span`, `facts`, `story`.
2. **[Edge](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py#L113):** A typed directed relationship (`CALLS`, `INVOKES`, `IMPORTS`, `CONTAINS`, `INHERITS`, `READS_FROM`, `WRITES_TO`, `CO_CHANGED_WITH`).
3. **[CanonicalGraph](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py#L131):** Holds `nodes: dict[str, NodeCard]` and `edges: list[Edge]`, wrapping a NetworkX `DiGraph`.
4. **[ContextPackage](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py#L224):** The compiled bundle delivered to coding agents, containing target seeds, blast radius, constraints, and formatted context.

---

## 4. What to Focus on vs What to Ignore

- **Focus On:** Everything inside [repopeek/](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/) and unit tests under [tests/](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/).
- **Ignore / Treat as External Fixture:**
  - `testing/da-assistant/`: This is an external evaluation workspace used for benchmarking agent task completion. Do not attempt to run its internal tests or modify its application code.
  - `.repopeek/` and `output/`: Ephemeral generated build artifacts.
