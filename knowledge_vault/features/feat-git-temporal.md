---
id: feat-git-temporal
type: feature
title: Git Temporal Intelligence & Co-Change Matrix
summary: Mines git commit history with exponential half-life time decay to construct pairwise co-change matrices and CO_CHANGED_WITH graph edges.
status: verified
tags: [git, temporal, co-change, blast-radius, probability]
code_refs: [repopeek/temporal/miner.py, repopeek/temporal/__init__.py, repopeek/models/schema.py, repopeek/graph/builder.py, repopeek/query/engine.py, repopeek/cli.py]
depends_on: ['[[feat-graph-construction]]', '[[plan-phase-3]]']
affects: ['[[log-phase-3]]']
last_verified: 2026-10-05
---

# Git Temporal Intelligence & Co-Change Matrix

## 1. Executive Summary & Purpose
Software components frequently possess hidden coupling not visible through static AST imports or call graphs (e.g. database schema migrations accompanied by ORM models, configuration updates accompanied by handler changes, or parallel frontend/backend adjustments). `GitTemporalMiner` extracts this historical co-evolution from git commit logs, weighting recency via exponential half-life decay, and adds `CO_CHANGED_WITH` relational edges to the code property graph.

## 2. Mathematical Formulation
1. **Exponential Time Decay:**
   For commit $c$ with age in days $age\_days = (t_{ref} - t_c) / 86400$:
   $$w_c = \exp\left(-\frac{\ln(2) \cdot age\_days}{t_{1/2}}\right)$$
   where $t_{1/2} = 180$ days default half-life. A commit from today receives weight 1.0; a commit from 6 months ago receives weight 0.5.
2. **Conditional Co-Change Probability:**
   For files $A$ and $B$:
   $$P(B|A) = \frac{\sum_{c \in Commits(A \cap B)} w_c}{\sum_{c \in Commits(A)} w_c}$$
   Capped at 0.99 to reflect non-absolute empirical certainty.
3. **Graph Integration:**
   When $P(B|A) \ge 0.25$ and the pair has co-changed across at least 2 distinct commits, an edge `CO_CHANGED_WITH` connects file node $A$ to file node $B$ with evidence documenting $P(B|A)$ and commit co-occurrence count.

## 3. Query & CLI Interface
- `repopeek --co-changes <file_or_symbol>` returns ranked co-change dependencies.
- `GraphQueryEngine.co_changes(query)` exposes raw co-change statistics for agent workflows.
- `GraphBuilder.build_from_directory()` automatically synthesizes `CO_CHANGED_WITH` edges during whole-repo indexing.
