# Workflow Index

This directory documents the end-to-end operational, data, and control workflows executed within RepoPeek.

---

## Catalog of Documented Workflows

| Document | Workflow Name | Trigger / Initiator | Core Modules Involved |
|---|---|---|---|
| [01-Primary-Workflow.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/01-Primary-Workflow.md) | **Repository Ingestion & Full Graph Construction** | CLI (`repopeek --repo-path`) | `discovery`, `parsers`, `graph`, `enrichment`, `storage` |
| [02-Data-Flow.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/02-Data-Flow.md) | **Data Flow & Object Transformation** | System-wide | `DiscoveredFile` -> `ParseResult` -> `CanonicalGraph` -> `ContextPackage` |
| [03-Control-Flow.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/03-Control-Flow.md) | **Control Flow, Branching & Loops** | System-wide | CLI dispatch, bottom-up topological sort, BFS blast radius, MCP loop |
| [04-Error-Handling.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/04-Error-Handling.md) | **Error Handling, Fallbacks & Recovery** | Syntax/API errors | Resilient fallback parsers, LLM retries, FactVerifier rejections |
| [05-Configuration-Flow.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/05-Configuration-Flow.md) | **Configuration Precedence & Options** | CLI flags / Config file | `RepopeekConfig`, environment variables, CLI overrides |
| [06-Startup-and-Initialization.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/06-Startup-and-Initialization.md) | **Startup & Bootstrapping Sequences** | CLI invocation | Engine loading, SQLite initialization, MCP server initialization |
| [07-Shutdown-and-Cleanup.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/07-Shutdown-and-Cleanup.md) | **Shutdown & Resource Management** | Signal / CLI completion | Thread shutdown, SQLite commit, atomic swap cleanup |
| [08-Query-and-Context-Compilation.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/08-Query-and-Context-Compilation.md) | **Intent Resolution & Context Compilation** | CLI / MCP tool call | `retrieval.intent`, `graph.blast_radius`, `context.compiler` |
| [09-Incremental-Watch-and-Sync.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/09-Incremental-Watch-and-Sync.md) | **Incremental Watch & Fast Sync (<50ms)** | Filesystem event / daemon | `daemon.watcher`, `graph.builder`, `storage.json_store` |
| [10-Evaluation-and-Benchmarking.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/10-Evaluation-and-Benchmarking.md) | **4-Level Benchmark Evaluation** | CLI (`--evaluate`) | `evaluation.benchmark`, `dataset`, `report` |

---

## How to Read Workflow Documents

Every workflow document answers:
- **Initiator:** Who or what starts the workflow?
- **Entry Point:** Exact code file and function where execution begins.
- **Inputs & Validation:** Data types, schemas, and preconditions.
- **Transformations & Logic:** Detailed execution steps and formulas.
- **Side Effects & Persistence:** File writes, database mutations, external calls.
- **Failure Modes & Retries:** Error recovery mechanisms.
- **Verification Tests:** Test suites confirming the behavior.
