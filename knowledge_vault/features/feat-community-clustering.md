---
id: feat-community-clustering
type: feature
title: Unsupervised Community Detection & Clustering Engine
summary: Deterministic graph partitioning into modular functional communities using Leiden and Louvain with cohesion scoring and semantic naming.
status: active
tags: [phase4, clustering, louvain, leiden, communities]
code_refs: [repopeek/graph/clustering.py]
depends_on: ['[[feat-polyglot-engine]]', '[[plan-phase-4]]', '[[moc-features]]']
affects: ['[[feat-graph-analysis]]', '[[feat-graph-report]]', '[[feat-wiki-export]]']
last_verified: 2026-10-12
---

# Unsupervised Community Detection & Clustering Engine

## Purpose
Partitions complex repository code graphs into cohesive functional communities to expose subsystem modularity, boundary couplings, and architectural organization.

## Behavior / Contract
- `detect_communities`: Constructs undirected NetworkX projection and partitions nodes using Leiden (graspologic) or deterministic Louvain (`networkx.algorithms.community.louvain_communities`).
- `compute_cohesion_scores`: Evaluates density of internal edges against theoretical maximum ($0.0 \dots 1.0$).
- `generate_community_labels`: Automatically derives human/agent-readable module titles from predominant directory paths and hub symbols.
- Splits oversized communities exceeding threshold fraction.

## Impact
- **Depends on:** [[feat-polyglot-engine]], [[plan-phase-4]], [[moc-features]]
- **Affects:** [[feat-graph-analysis]], [[feat-graph-report]], [[feat-wiki-export]]

## Related
[[feat-graph-analysis]], [[moc-features]]
