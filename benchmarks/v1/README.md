# RepoPeek Benchmark Suite — Version 1 (Frozen)

## Overview

This directory contains the frozen **v1 Benchmark Suite** for evaluating RepoPeek empirically across four core levels:

```text
Level 1: Task → Symbol Retrieval
Level 2: Symbol → Dependency / Impact Graph
Level 3: Task → Compiled Context
Level 4: Context → Coding-Agent Task Performance
```

The benchmark answers whether RepoPeek enables an AI coding agent to solve repository-level tasks with **less context, fewer tool calls, fewer irrelevant files, and equal or higher correctness**.

---

## Dataset Structure

The benchmark suite (`tasks.yaml`) contains 50 grounded tasks divided into six core categories:

1. **A. Local behavior (`local_001` - `local_009`):** Direct method/attribute edits, signature updates, and parameter tuning.
2. **B. Dependency impact (`dep_010` - `dep_018`):** Downstream and upstream caller/callee reasoning, base class mutation, and blast radius.
3. **C. Cross-language (`cross_019` - `cross_026`):** Python FastAPI route handlers connected to TypeScript client callers, SQL queries, and shell scripts.
4. **D. Historical behavior (`hist_027` - `hist_034`):** Git commit co-change mining, chronological predictions, and exponential half-life verification.
5. **E. Negative retrieval (`neg_035` - `neg_042`):** Intentional task constraints testing whether RepoPeek prunes irrelevant directories and prevents false inclusion.
6. **F. Multi-hop tasks (`multi_043` - `multi_050`):** Multi-tier flow tracing across 3+ hops from entrypoint through data schemas to deployment scripts.

---

## Execution Instructions

Run the complete evaluation suite via the RepoPeek CLI:

```bash
# Run full evaluation across all levels
repopeek evaluate

# Custom dataset and custom output destinations
repopeek evaluate \
  --dataset benchmarks/v1/tasks.yaml \
  --output benchmark-results.json \
  --report benchmark-report.md

# Evaluate a specific level
repopeek evaluate --eval-level retrieval
repopeek evaluate --eval-level graph
repopeek evaluate --eval-level context
```

---

## Freeze Protocol

- **Dataset immutability:** `tasks.yaml` is frozen. No task descriptions or gold references may be modified to artifically boost scores.
- **Leakage prevention:** Gold metadata is consumed solely by the evaluation harness. The RepoPeek pipeline receives only `(task, repository)` inputs.
- **Temporal integrity:** Commit history evaluations strictly enforce chronological cutoffs. No future commits are used during co-change prediction training.
- **Honest Level 4 status:** Unless live agent executions have been run and recorded, Level 4 agent results remain marked as `Agent-level improvement has NOT been demonstrated yet.`
