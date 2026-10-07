# RepoPeek Documentation Hub

## Project Summary

RepoPeek is a local-first Semantic Code Property Graph (SCPG) and repository intelligence engine. It parses polyglot software codebases (Python, TypeScript, JavaScript, SQL, Shell, JSON, YAML) into a deterministic graph substrate of atomic entities (`NodeCard`) and directed relational dependencies (`Edge`). 

On top of this graph substrate, RepoPeek layers:
1. A 5-tier semantic story cascade that enriches symbols with verified natural language summaries while preventing hallucinations.
2. A mathematical traversal engine calculating distance-decayed confidence scores and evidence-backed blast radius trees (`direct`, `indirect`, `excluded`).
3. An offline task-to-symbol intent resolver combining AST identifier analysis, SQLite FTS5 BM25 search, and Reciprocal Rank Fusion (RRF).
4. A Context Compiler that packages minimal, token-budgeted context slices (<500 to 1500 tokens) with multi-tier constraint enforcement and risk-assessed step-by-step change plans for autonomous coding agents.
5. Standard interfaces including a stdio JSON-RPC Model Context Protocol (MCP) server, an interactive browser-based force-directed graph viewer, an Obsidian vault exporter, and a background incremental file synchronization daemon.

RepoPeek operates entirely locally with zero mandatory external database, GPU, or vector store dependencies.

**Current product ceiling (2026-10-06):** context packs are **≤4 files + ~40-line spans (~1–2k tokens)**, not a guaranteed sub-500-token closed world. See [06-Dais-Real-World-Evaluation.md](06-Dais-Real-World-Evaluation.md) and [07-Agent-Handoff.md](07-Agent-Handoff.md).

---

## Core Problem Statement

AI coding agents (e.g. Claude Code, Cursor, Antigravity, SWE-bench runners) face fundamental operational bottlenecks when working on complex codebases:
- **Context Window Exhaustion:** Full file reading and naive grep dumps burn hundreds of thousands of tokens on boilerplate, leading to cognitive degradation ("lost-in-the-middle") and high financial cost.
- **Hidden Blast Radius:** Changing a function often breaks downstream callers, database queries, shell scripts, or API routes located across different files or languages that standard ASTs cannot connect.
- **Hallucinated Edits:** Without deterministic constraints on signatures, types, exceptions, and schema tables, agents generate plausible code that fails at runtime.
- **Stale Context:** In long agent sessions, file edits invalidate static context packs unless graph updates synchronize incrementally in milliseconds.

RepoPeek solves these challenges by providing sub-500-token, high-precision context packages and exact blast-radius predictions with zero file-read overhead.

---

## High-Level System Operation

```text
Repository Files (.py, .ts, .js, .sql, .sh, .json, .yaml)
                       │
                       ▼
             [01: Discovery & Hashing]
      (crawler.py, classifier.py, hasher.py)
                       │
                       ▼
             [02: Polyglot Parsers]
  (python.py, typescript.py, sql.py, shell.py, config.py)
                       │
                       ▼
             [03: Graph Assembly]
 (builder.py: AST nodes, local edges, git provenance)
                       │
                       ▼
             [04: Cross-File Resolution]
  (resolver.py: imports, calls, inherits, env vars, data)
  (bridges/http.py: client fetch/axios -> server routes)
  (temporal/miner.py: git commit co-change edges)
                       │
                       ▼
             [05: Canonical Graph]
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
[06: 5-Tier Story Cascade]   [07: Persistence & Sharding]
  - Trivial filter             - graph.json
  - SHA-256 hash cache         - lenses/*.json (9 lenses)
  - Groq LLM inference         - shards/*.json
  - FactVerifier check         - cache.db (SQLite + FTS5)
       │                               │
       └───────────────┬───────────────┘
                       │
                       ▼
          [08: Query & Serving Engine]
 (engine.py, intent.py, blast_radius.py, compiler.py)
                       │
  ┌───────────────┬────┴──────────┬───────────────┐
  ▼               ▼               ▼               ▼
MCP Server    CLI Query     Web Viewer     Obsidian Vault
(10 tools)    (30+ flags)   (Port 8765)     (Wikilinks)
```

---

## Major Subsystems

| Subsystem | Primary Modules | Primary Responsibility |
|---|---|---|
| **Discovery Substrate** | [`repopeek/discovery/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery) | Traverses repository, enforces ignore rules, classifies file types, and computes SHA-256 and git blob SHAs. |
| **Polyglot Parsers** | [`repopeek/parsers/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers) | Deterministic syntactic extraction across Python, TypeScript/JavaScript, SQLGlot, Shell, and JSON/YAML. |
| **Graph & Resolution** | [`repopeek/graph/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/graph) | Assembles `CanonicalGraph`, resolves cross-file symbols, imports, and variables; computes 9 lenses. |
| **Bridges & Temporal** | [`repopeek/bridges/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/bridges), [`repopeek/temporal/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/temporal) | Maps client API calls to server endpoints; mines git history with half-life decay for co-change edges. |
| **Story Cascade** | [`repopeek/enrichment/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/enrichment), [`repopeek/llm/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/llm) | 5-tier semantic enrichment pipeline with strict `FactVerifier` anti-hallucination checks. |
| **Retrieval & Intent** | [`repopeek/retrieval/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval) | Normalizes natural language queries, extracts code identifiers, and ranks candidates via AST + BM25 + RRF. |
| **Context Compiler** | [`repopeek/context/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/context) | Packages token-budgeted context (Levels 1-3) with mathematical blast radius and step-by-step change plans. |
| **Storage & Caching** | [`repopeek/storage/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage) | Content-addressed sharding with atomic directory swap, SQLite recursive CTE cache, and FTS5 tables. |
| **Daemon & Serving** | [`repopeek/daemon/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/daemon), [`repopeek/query/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query), [`repopeek/viewer/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/viewer) | Real-time <50ms file watcher, stdio JSON-RPC MCP server (10 tools), force-directed web viewer. |
| **Evaluation Suite** | [`repopeek/evaluation/`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/evaluation) | 4-level benchmarking harness measuring MRR, Recall@k, token reduction, Brier calibration, and latency. |

---

## Critical Workflows at a Glance

1. **Repository Ingestion & Indexing:** Executed via `python -m repopeek.cli --repo-path <path> [--offline]`. Builds full canonical property graph, runs story cascade, outputs sharded JSON artifacts and SQLite cache.
2. **Intent Resolution & Symbol Lookup:** `python -m repopeek.cli --resolve "<task>"`. Converts prompt into query components, searches AST identifiers and FTS5, applies 6-component scoring.
3. **Blast Radius Analysis:** `python -m repopeek.cli --impact <target>`. Performs multi-hop BFS traversal calculating path decay, combined multi-path confidence, and direct/indirect/excluded classification.
4. **Context Package Compilation:** `python -m repopeek.cli --context "<task>" --budget 1500 --level 2`. Produces structured Markdown containing entrypoints, blast radius, constraints, and actionable change plan.
5. **Incremental Watch Synchronization:** `python -m repopeek.cli --watch`. Background daemon detects file modifications and updates graph nodes, edges, shards, and SQLite rows in <50ms without full rebuilds.
6. **Agent MCP Tool Serving:** `python -m repopeek.cli --serve-mcp`. Exposes 10 JSON-RPC tools over stdio for IDE integration.

---

## Getting Started

### For Senior Engineers

1. Review [01-System-Overview.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/01-System-Overview.md) to understand end-to-end data lifecycle and runtime boundaries.
2. Review [03-Architecture.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/03-Architecture.md) for logical component interaction and mathematical formulas.
3. Inspect [02-Repository-Map.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/02-Repository-Map.md) to locate exact code modules.
4. Run tests: `$env:PYTHONPATH="."; .venv\Scripts\python -m pytest tests` (Windows PowerShell).

### For AI Coding Agents

1. **Start Here:** Read [ai-agent/00-Agent-Entry-Guide.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/ai-agent/00-Agent-Entry-Guide.md).
2. Follow the 8-step decision process before proposing any code edit.
3. Check [constraints/05-Negative-Constraints.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/constraints/05-Negative-Constraints.md) and [ai-agent/05-Common-Mistakes.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/ai-agent/05-Common-Mistakes.md) to avoid known failure modes.

---

## How to Trace Features and Bugs

### Tracing a Feature
1. **Identify Entry Point:** Look up CLI argument handling in [`repopeek/cli.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/cli.py) or MCP tool in [`repopeek/query/mcp_server.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/mcp_server.py).
2. **Follow Engine Dispatch:** Follow the call into [`repopeek/query/engine.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/engine.py).
3. **Follow Core Processing:** Step into the domain module (`retrieval/intent.py`, `graph/blast_radius.py`, `context/compiler.py`, etc.).
4. **Follow State Mutation:** Follow serialization into [`repopeek/storage/json_store.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/json_store.py) or [`repopeek/storage/sqlite_cache.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/sqlite_cache.py).
5. **Inspect Test Coverage:** Consult corresponding test file in `tests/`.

### Tracing a Bug
1. Check [known-issues/00-Known-Issues.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/known-issues/00-Known-Issues.md) to see if the defect is cataloged (e.g. RP-001 through RP-008).
2. Run explain mode: `python -m repopeek.cli --explain "<query>"` to inspect retrieval scoring and tokenization.
3. Inspect blast radius report: `python -m repopeek.cli --impact <target>` to verify edge confidence and exclusions.
4. Check test cases in `tests/test_retrieval_reliability.py` or `tests/test_golden_scenarios.py`.

---

## Critical Invariants and Constraints

- **Determinism Over Guesswork:** If an entity or relationship can be extracted statically from AST, an LLM must NEVER be used.
- **Fact Verification Boundary:** LLM-generated summaries must pass AST fact verification (`reads`, `writes`, `raises`, `calls`). Any contradiction causes immediate fallback to deterministic templates.
- **Zero Heavy Runtime Dependencies:** Core graph indexing, SQLite traversal, FTS5 BM25 retrieval, and mathematical blast radius MUST NOT depend on external server daemons, vector databases, or heavy ML libraries.
- **Negative Constraints Are Enforced:** Excluded paths and symbols specified in user prompts must be pruned from blast radius propagation and never suggested as candidate entrypoints.
- **Atomic Persistence:** Graph writes use staging directories and atomic directory swaps to prevent partial write corruption.

---

## Documentation Navigation Map

```text
Workflow_Documentation/
│
├── 00-README.md                           <-- You are here
├── 01-System-Overview.md                  <-- System architecture & runtime boundaries
├── 02-Repository-Map.md                   <-- Complete directory & symbol breakdown
├── 03-Architecture.md                     <-- Deep architectural diagrams & formulas
├── 04-Component-Responsibilities.md       <-- Component contracts & non-responsibilities
├── 05-Engineering-Completion-Report.md    <-- MVP lock before/after and remaining gaps
├── 06-Dais-Real-World-Evaluation.md       <-- dais agent vs RepoPeek+agent graduation
├── 07-Agent-Handoff.md                    <-- copy-paste prompt for the next coding agent
├── 00-Documentation-Status.md             <-- Coverage, confidence, and audit report
│
├── workflows/                             <-- End-to-end execution flows
│   ├── 00-Workflow-Index.md
│   ├── 01-Primary-Workflow.md             <-- Ingestion & graph construction
│   ├── 02-Data-Flow.md                    <-- Object lifecycles & transformations
│   ├── 03-Control-Flow.md                 <-- Branching, recursion, dispatch loops
│   ├── 04-Error-Handling.md               <-- Failure paths & recovery mechanisms
│   ├── 05-Configuration-Flow.md          <-- Configuration precedence & options
│   ├── 06-Startup-and-Initialization.md   <-- Bootstrapping sequences
│   ├── 07-Shutdown-and-Cleanup.md         <-- Process cleanup & resource management
│   ├── 08-Query-and-Context-Compilation.md<-- Intent -> Blast Radius -> Context Package
│   ├── 09-Incremental-Watch-and-Sync.md   <-- <50ms daemon synchronization
│   └── 10-Evaluation-and-Benchmarking.md  <-- 4-level evaluation execution
│
├── components/                            <-- In-depth component documentation
│   ├── 00-Component-Index.md
│   ├── 01-Discovery-and-Classification.md
│   ├── 02-Polyglot-Parsers.md
│   ├── 03-Graph-Builder-and-Symbol-Resolver.md
│   ├── 04-Mathematical-Blast-Radius-Engine.md
│   ├── 05-Semantic-Enrichment-and-Verification-Pipeline.md
│   ├── 06-Hybrid-Retrieval-and-Intent-Engine.md
│   ├── 07-Context-Compiler-and-Change-Planner.md
│   ├── 08-Cross-Language-HTTP-Bridge.md
│   ├── 09-Git-Temporal-Miner.md
│   ├── 10-Storage-and-SQLite-Cache.md
│   ├── 11-Incremental-Watch-Daemon.md
│   ├── 12-MCP-Server-and-Interactive-Viewer.md
│   └── 13-Evaluation-and-Benchmarking-Suite.md
│
├── data/                                  <-- Schemas and persistence
│   ├── 00-Data-Model-Index.md
│   ├── 01-Data-Structures.md              <-- Pydantic & Dataclass specifications
│   ├── 02-Data-Lifecycle.md               <-- Creation, mutation, persistence lifecycle
│   └── 03-Persistence.md                  <-- JSON sharding, SQLite schema, FTS5
│
├── interfaces/                            <-- Public contracts
│   ├── 00-Interface-Index.md
│   ├── 01-Internal-APIs.md                <-- Python SDK interfaces
│   ├── 02-External-APIs.md                <-- MCP tools, HTTP endpoints, LLM API
│   └── 03-CLI.md                          <-- Command-line interface manual
│
├── operations/                            <-- Operational playbooks
│   ├── 00-Operations-Index.md
│   ├── 01-Installation.md
│   ├── 02-Development-Workflow.md
│   ├── 03-Testing.md
│   ├── 04-Build-and-Release.md
│   ├── 05-Deployment.md
│   ├── 06-Monitoring.md
│   └── 07-Troubleshooting.md
│
├── decisions/                             <-- Architectural Decision Records
│   ├── 00-Decision-Index.md
│   └── 01-Architectural-Decision-Records.md
│
├── constraints/                           <-- System boundaries
│   ├── 00-Constraint-Index.md
│   ├── 01-Technical-Constraints.md
│   ├── 02-Behavioral-Invariants.md
│   ├── 03-Performance-Constraints.md
│   ├── 04-Security-Constraints.md
│   └── 05-Negative-Constraints.md         <-- What the system MUST NOT do
│
├── dependencies/                          <-- Dependency analysis
│   ├── 00-Dependency-Index.md
│   └── 01-Dependency-Analysis.md
│
├── testing/                               <-- Test suite structure
│   ├── 00-Test-Strategy.md
│   ├── 01-Test-Architecture.md
│   └── 02-Coverage-and-Gaps.md
│
├── known-issues/                          <-- Catalog of bugs & discrepancies
│   └── 00-Known-Issues.md
│
└── ai-agent/                              <-- Playbook for future AI agents
    ├── 00-Agent-Entry-Guide.md
    ├── 01-How-to-Understand-the-Repository.md
    ├── 02-How-to-Trace-a-Workflow.md
    ├── 03-How-to-Safely-Modify-Code.md
    ├── 04-Important-Constraints.md
    └── 05-Common-Mistakes.md
```
