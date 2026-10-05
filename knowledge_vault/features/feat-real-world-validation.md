---
id: feat-real-world-validation
type: feature
title: Real-World Validation Experiment (da-assistant)
summary: Controlled 12-task empirical evaluation on a non-synthetic Next.js + Django + Neo4j repository demonstrating 70% token savings, 65% exploration reduction, and isolating 8 architectural defects (P0-P3).
status: verified
tags: [evaluation, real-world, da-assistant, benchmark, issues, empirical]
code_refs: [testing/da-assistant/run_experiment.py, testing/da-assistant/FINAL-REPORT.md, testing/da-assistant/REPOPEEK-ISSUES.md, testing/da-assistant/results/comparison.md, testing/da-assistant/tasks.yaml]
depends_on: ['[[feat-evaluation-benchmarking]]', '[[moc-features]]']
affects: ['[[log-phase-3]]']
last_verified: 2026-10-05
---

# Real-World Validation Experiment (da-assistant)

## 1. Executive Summary & Objective
To validate RepoPeek against a real, non-synthetic production codebase, a controlled empirical experiment was conducted against `da-assistant` (Next.js 14, Django 5.0 + DRF, Neo4j 5.20, Celery/Redis, LangChain RAG; 263 files, 1,598 nodes, 10,181 edges).

The evaluation answered whether RepoPeek helps a coding agent understand and modify a real software repository better than the same agent operating normally.

## 2. Key Empirical Findings
- **Exploration Tool Calls:** Reduced by **64.6%** (from 14.7 down to 5.2 calls per task).
- **Files Inspected:** Reduced by **79.4%** (from 10.7 down to 2.2 files per task).
- **Token Consumption:** Reduced by **69.9%** across all 12 tasks (from 196,798 down to 59,252 total tokens).
- **Context Recall:** Averaged **86.1%**, achieving **100% recall on 10 of 12 tasks**.
- **Context Precision:** Averaged **0.57%** (0.22% to 1.21%), indicating high false-positive noise in the compiled 1-hop and 2-hop blast radius.
- **Success Rate:** 75.0% (9/12 tasks passed) at parity with the baseline.

## 3. Discovered Architectural Issues
1. **RP-003 (P0 - Critical):** Unnamespaced identifier collision (`next`, `re.sub`) caused cross-language graph traversal explosion (`--impact fetchClients` returned 190,462 lines of JSON across 831 nodes).
2. **RP-001 (P1 - High):** Total blindspot for Django/DRF declarative `urlpatterns = [path(...)]` routes in `repopeek/bridges/http.py`.
3. **RP-002 (P1 - High):** Inability to trace client HTTP requests wrapped in custom helpers (`request<T>()`).
4. **RP-005 (P1 - High):** Context precision collapse due to lack of neighbor reranking in `ContextCompiler`.
5. **RP-004 (P2 - Medium):** Naive `"table"` substring check misclassifying Python functions/tests as SQL tables.
6. **RP-006 (P2 - Medium):** Lexical token overlap ranking `docker-compose.yml` ahead of application code.
7. **RP-007 (P2 - Medium):** Negative constraint phrases ("do not modify") inverted into positive relevance signals.

Full report and evidence stored in `testing/da-assistant/FINAL-REPORT.md` and `testing/da-assistant/REPOPEEK-ISSUES.md`.
