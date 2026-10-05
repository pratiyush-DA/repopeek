---
id: feat-evaluation-benchmarking
type: feature
title: Agent Evaluation and Benchmarking Subsystem
summary: Reproducible 4-level evaluation framework measuring task retrieval, graph accuracy, confidence calibration, temporal intelligence, and context reduction.
status: verified
tags: [evaluation, benchmark, metrics, retrieval, calibration, context]
code_refs: [repopeek/evaluation/models.py, repopeek/evaluation/metrics.py, repopeek/evaluation/dataset.py, repopeek/evaluation/retrieval.py, repopeek/evaluation/graph.py, repopeek/evaluation/temporal.py, repopeek/evaluation/context.py, repopeek/evaluation/benchmark.py, repopeek/evaluation/report.py, repopeek/cli.py, tests/test_evaluation.py, tests/test_retrieval_reliability.py]
depends_on: ['[[plan-phase-3]]', '[[moc-features]]']
affects: ['[[log-phase-3]]']
last_verified: 2026-10-05
---

# Agent Evaluation and Benchmarking Subsystem

## 1. Executive Summary & Purpose
The evaluation subsystem establishes a reproducible, empirically grounded benchmark for measuring whether RepoPeek enables AI coding agents to solve repository-level tasks with less context, fewer tool calls, fewer irrelevant files, and higher precision.

## 2. Four-Level Evaluation Architecture
1. **Level 1 (Task → Symbol Retrieval):** Evaluates AST identifier search, SQLite FTS5 BM25, and multi-component ranking against ground truth symbols. Computes Candidate Recall@50, Candidate Recall@100, Final Recall@1, Recall@3, Recall@5, Recall@10, and Mean Reciprocal Rank (MRR). Includes automated 4-tier ablation tracking (Baseline vs +Identifier Normalization vs +Stemming vs +Compound Variants).
2. **Level 2 (Symbol → Dependency / Impact Graph):** Measures traversal precision, recall, and F1 across depths 1 through 4 hops. Validates probabilistic edge confidence using Brier score and 10 calibration buckets ($[0.0, 0.1), \dots, [0.9, 1.0]$).
3. **Level 3 (Task → Compiled Context):** Quantifies context recall (symbols, files, tests, constraints), context precision, token reduction percentage vs full-file baseline, and negative retrieval precision (verifying zero false inclusions of explicitly excluded paths/symbols).
4. **Level 4 (Context → Agent Outcomes):** Provides standard `AgentRunner` adapter interface (`BaselineAgent` vs `RepoPeekAgent`) for controlled LLM coding agent benchmarking without fabricated metrics.

## 3. Temporal Intelligence & Chronological Split
Git co-change predictions enforce strict chronological cutoff splits to eliminate future leakage: historical commits before the cutoff train pairwise correlation models across multiple half-lives (30, 90, 180, 365 days), and predictions are evaluated against subsequent commits.

## 4. CLI Operation & Reporting
- Execute evaluation: `repopeek evaluate`
- Custom options: `repopeek evaluate --dataset benchmarks/v1/tasks.yaml --output benchmark-results.json --report benchmark-report.md`
- Outputs machine-readable JSON and human-readable Markdown with automated failure categorization (`LEXICAL_MISS`, `IDENTIFIER_MISS`, `RANKING_ERROR`, `GRAPH_MISSING_EDGE`, `NEGATIVE_RETRIEVAL_FAILURE`).
