# Documentation Status and Coverage Audit

**As of 2026-10-06:** treat this audit as historical. Live code paths: blast radius `repopeek/graph/blast_radius.py`, compiler `repopeek/context/compiler.py`, intent `repopeek/retrieval/intent.py`, MCP `repopeek/query/mcp_server.py`. New-agent prompt: [07-Agent-Handoff.md](07-Agent-Handoff.md). Dais metrics: [06-Dais-Real-World-Evaluation.md](06-Dais-Real-World-Evaluation.md). Pytest: `python -m pytest tests` (~197 tests). README MCP table is 10 tools; Groq default is `qwen/qwen3.8-27b`.

---

This document is the final verification deliverable for the RepoPeek workflow documentation system. It provides an exhaustive audit of documentation coverage, major workflows, architectural components, discovered constraints, verified code discrepancies, known gaps, and confidence ratings.

---

## 1. Documentation Coverage Summary

A complete, standalone documentation system consisting of **67 comprehensive technical documents** has been generated inside [Workflow_Documentation/](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/):

| Directory | Document Count | Focus Areas |
|---|---|---|
| **Root (`/`)** | 6 files | Master README, System Overview, Repository Map, Architecture, Component Responsibilities, Status Audit. |
| **`workflows/`** | 11 files | End-to-end execution flows: Primary build, Data flow, Control flow, Error handling, Config flow, Startup, Shutdown, Context compilation, Watch sync, Evaluation. |
| **`components/`** | 14 files | Deep specifications for all 13 architectural components with responsibilities, boundaries, key symbols, and failure modes. |
| **`data/`** | 4 files | Complete Pydantic schemas, object lifecycle state machines, atomic staging swap, and SQLite FTS5 persistence. |
| **`interfaces/`** | 4 files | Internal Python SDK, 10 stdio MCP tools, Web Viewer REST endpoints, Groq LLM integration, and complete 30+ flag CLI reference. |
| **`operations/`** | 8 files | Installation, dev workflow, Pytest execution with fixture trap warnings, build packaging, deployment models, monitoring, and troubleshooting runbooks. |
| **`decisions/`** | 2 files | Formal Architectural Decision Records (ADR-001 through ADR-007) with trade-offs and alternatives. |
| **`constraints/`** | 6 files | Technical limits, behavioral invariants, performance latency budgets, security trust boundaries, and first-class negative constraints. |
| **`dependencies/`** | 2 files | Deep third-party library analysis (`networkx`, `sqlglot`, `pydantic`, `ruamel.yaml`) and stdlib utilization. |
| **`testing/`** | 3 files | Test philosophy, 25-suite test architecture, fixture layout, verified behaviors, and uncovered edge cases. |
| **`known-issues/`** | 1 file | Detailed defect ledger (RP-001 through RP-010) covering confirmed bugs, technical debt, and architectural risks. |
| **`ai-agent/`** | 6 files | 8-step actionable entry playbook, repository understanding guide, workflow tracing walkthrough, safe modification protocol, constraints, and common mistakes. |

---

## 2. Major Workflows Discovered and Documented

1. **Full Repository Crawling & Ingestion:** `.gitignore` parsing, MIME classification, content hashing.
2. **Polyglot Parsing & AST Extraction:** Python AST, TypeScript/JavaScript regex state machine, SQL AST (`sqlglot` + `sqlparse`), Docker Compose YAML.
3. **Cross-Language HTTP Boundary Bridging:** Wildcard route normalization (`/api/users/:id`), fetch to backend handler matching, `INVOKES` edge creation.
4. **Graph Assembly & Symbol Resolution:** Qualified ID minting (`file::symbol`), lookup index construction, NetworkX `DiGraph` population.
5. **Semantic Enrichment Fallback Cascade:** 5-tier cascade (Cached Story $\to$ AST Docstrings $\to$ AST Invariants $\to$ Offline Heuristics $\to$ Groq Cloud LLM).
6. **Fact Verification & Hallucination Pruning:** `FactVerifier` cross-checking LLM claims against AST purity and side effects.
7. **Deterministic Sharded Persistence:** Sorted JSON serialization, 9 materialized lenses, file shards, atomic directory rename swap.
8. **Derived SQLite Cache Compilation:** Table population, recursive CTE traversal indexing, FTS5 virtual table tokenization.
9. **Dual-Channel Hybrid Retrieval:** Channel 1 (Code Token Match) + Channel 2 (BM25 FTS5) fused via Reciprocal Rank Fusion ($k=60$).
10. **Mathematical Blast Radius Propagation:** Upstream BFS traversal, path decay ($0.85^d$), multi-path Noisy-OR combination, 5-tier risk sorting.
11. **Progressive Context Compilation & Planning:** Token budget compaction (8k cap), Level 1-3 progressive disclosure, topological change plan generation.
12. **Incremental Watch & Real-Time Sync:** Inode mtime polling, single-file AST re-parse, `<50ms` graph update.
13. **Stdio MCP Agent Serving:** 10 JSON-RPC 2.0 tools serving autonomous AI coding agents.
14. **Benchmarking & Evaluation:** Automated computation of Mean Reciprocal Rank (MRR), Precision@K, and Brier calibration scores.

---

## 3. Major Architectural Components Discovered

1. **RepoCrawler & Classifier** ([repopeek/discovery/](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/))
2. **Polyglot AST Parsers** ([repopeek/parsers/](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/))
3. **GraphBuilder & Symbol Resolver** ([repopeek/graph/builder.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/graph/builder.py))
4. **Cross-Language HTTP Bridge** ([repopeek/bridges/http.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/bridges/http.py))
5. **Mathematical Blast Radius Engine** ([repopeek/analysis/blast_radius.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/analysis/blast_radius.py))
6. **Semantic Enrichment Pipeline & FactVerifier** ([repopeek/enrichment/](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/enrichment/))
7. **Hybrid Retrieval Engine** ([repopeek/retrieval/engine.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval/engine.py))
8. **ContextCompiler & Change Planner** ([repopeek/retrieval/context_compiler.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval/context_compiler.py))
9. **Git Temporal Miner** ([repopeek/temporal/miner.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/temporal/miner.py))
10. **Storage Engine & SQLite Cache** ([repopeek/storage/](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/))
11. **Incremental Watch Daemon** ([repopeek/watcher/daemon.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/watcher/daemon.py))
12. **Agent MCP Server** ([repopeek/query/mcp_server.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/mcp_server.py))
13. **Interactive Web Viewer** ([repopeek/viewer/server.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/viewer/server.py))
14. **Evaluation & Benchmarking Suite** ([repopeek/evaluation/](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/evaluation/))

---

## 4. Important Constraints and Invariants Discovered

- **Determinism:** Identical source code strictly produces byte-identical JSON outputs and SHA-256 checksums across runs.
- **Cycle Termination:** All traversals enforce visited sets, probability attenuation ($0.85^d$), and depth limits ($H \le 3$).
- **Fact Integrity:** LLM stories are subordinated to static AST facts; contradictions are pruned by `FactVerifier`.
- **Atomic Persistence:** In-place JSON modifications are prohibited; staging in `.tmp_build_<uuid>` followed by atomic directory swap guarantees zero half-written states.
- **Zero Target Code Modification:** RepoPeek is read-only with respect to target repository source code and git history.
- **Namespace Collision Isolation:** Unnamespaced identifiers (e.g. `next`) must be scoped by language/package prefix to prevent cross-language graph explosion (RP-003).
- **Stdio Stream Purity:** MCP servers must strictly route logs to `sys.stderr` to prevent JSON-RPC framing corruption.
- **Zero Emojis:** Strictly prohibited across all code, logs, commits, and documentation.

---

## 5. Code vs Documentation Contradictions Discovered

| Topic | Existing Documentation Claim | Codebase Ground Truth | Status |
|---|---|---|---|
| **MCP Tool Inventory** | `README.md` documents only 5 tools (`lookup`, `neighbors`, `impact`, `data_trace`, `context_pack`). | [repopeek/query/mcp_server.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/mcp_server.py) exports **10 tools** (adding `repopeek_context`, `repopeek_plan`, `repopeek_routes`, `repopeek_co_changes`, `repopeek_resolve`). | Verified code discrepancy. Code is ground truth. |
| **Default Groq LLM Model** | `README.md` claims Groq uses `llama-3.1-8b-instant`. | [repopeek/llm/groq.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/llm/groq.py#L28) configures `qwen/qwen3.8-27b` (fast/balanced) and `openai/gpt-oss-120b` (strong). | Verified code discrepancy. Code is ground truth. |
| **Supported File Extensions** | `repopeek/config.py` omits `.ts`, `.tsx`, `.js` from `supported_extensions`. | `repopeek/discovery/classifier.py` and `GraphBuilder` actively parse TypeScript. | Verified code discrepancy (Issue RP-009). |

---

## 6. Known Documentation Gaps & Human Confirmation Areas

- **Production Deployment Telemetry:** While local CLI, MCP, and container deployments are verified from code, actual production usage volume, server fleets, or external telemetry collectors are not defined in this repository.
- **Long-Term Parser Strategy:** Whether the team intends to remain indefinitely on the pure-Python regex state machine for TypeScript or eventually adopt Tree-sitter bindings requires human architectural confirmation.

---

## 7. Confidence Assessment

| Domain | Confidence Level | Rationale |
|---|---|---|
| **Architecture & Component Boundaries** | **High** | Verified against imports, class declarations, and instantiation chains. |
| **Workflows & Traversal Math** | **High** | Validated against mathematical formulas, BFS code, and passing unit tests. |
| **Data Models & Schemas** | **High** | Directly extracted from Pydantic models in `repopeek/models/schema.py`. |
| **Operational & Test Procedures** | **High** | Verified through active test suite execution (`pytest tests` passing 178 tests). |
| **External Interfaces & MCP Protocols** | **High** | Validated against MCP server tool registries, CLI arguments, and viewer routes. |
| **Historical Decisions & Evolution** | **Medium-High** | Grounded in git commit messages, knowledge vault ADRs, and codebase structure. |
