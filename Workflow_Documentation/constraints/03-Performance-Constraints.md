# Performance Constraints and Budgets

This document outlines the latency budgets, memory ceilings, token constraints, and execution thresholds designed into RepoPeek.

---

## 1. Latency Budgets

| Operation | Target Budget | Upper Bound | Mechanism |
|---|---|---|---|
| **Incremental File Sync** | `<50ms` | `100ms` | Inode mtime check + single-file AST re-parse in [repopeek/watcher/daemon.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/watcher/daemon.py) |
| **Symbol Lookup** | `<2ms` | `10ms` | In-memory Python hash map lookup by qualified ID |
| **1-Hop Neighbor Query** | `<5ms` | `15ms` | NetworkX `in_edges` / `out_edges` or indexed SQLite `idx_edges_src` |
| **Multi-Hop Blast Radius** | `<25ms` | `100ms` | Breadth-first search capped at depth $H=3$ with probability threshold pruning ($\ge 0.05$) |
| **Context Compilation** | `<50ms` | `150ms` | In-memory token budgeting and 5-tier node packing in [repopeek/retrieval/context_compiler.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval/context_compiler.py) |
| **Full Repository Indexing** | `<15s` (10k LOC) | `60s` (100k LOC) | Offline multi-threaded AST parsing (zero LLM latency) |

---

## 2. Token Budgets for Agent Context

- **Constraint:** Context packages generated for AI coding agents must strictly obey the requested token budget (default: 1,500 tokens; max default cap: 8,000 tokens).
- **Classification:** **Verified Invariant**.
- **Evidence:** Enforced in [repopeek/retrieval/context_compiler.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval/context_compiler.py#L90):
  - Tokens are estimated using the standard 4-characters-per-token heuristic:
    $$\text{tokens} = \frac{\text{len}(\text{text})}{4}$$
  - Nodes are packed progressively by risk tier (Tier 1 $\to$ Tier 2 $\to$ Tier 3).
  - If adding a node's full snippet causes total tokens to exceed `budget_tokens`, the compiler downgrades the representation to a signature (Tier 2) or symbol name (Tier 3) to prevent context window overflow.

---

## 3. Memory Ceilings

- **Constraint:** The in-memory `CanonicalGraph` and NetworkX structures must operate within standard developer workstation memory limits:
  - Repositories under 5,000 source files: `<250MB` RAM.
  - Repositories under 20,000 source files: `<1GB` RAM.
- **Classification:** **Strong Convention**.
- **Optimization Strategy:**
  - Nodes store code coordinates (`Span(file, start, end)`) rather than inlining full source file contents into RAM.
  - Heavy source snippets are read on-demand from disk during level 3 context pack requests.

---

## 4. SQLite Optimization Pragmas

During cache database generation in [repopeek/storage/sqlite_cache.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/storage/sqlite_cache.py#L24-L25):
- `PRAGMA synchronous = OFF;`: Disables disk sync barriers during batch inserts, yielding a $5\times$ write throughput increase.
- `PRAGMA journal_mode = MEMORY;`: Stores SQLite rollback journals purely in RAM, eliminating secondary disk writes.
- `PRAGMA query_only = ON;`: Enforces read-only safety during user query executions.
