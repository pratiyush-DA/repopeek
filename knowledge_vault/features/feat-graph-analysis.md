---
id: feat-graph-analysis
type: feature
title: Graph Topological Analysis Engine
summary: Topological analysis identifying god nodes, surprising cross-boundary connections, circular import cycles, and automated architectural questions.
status: active
tags: [phase4, analysis, topology, god-nodes, cycles]
code_refs: [repopeek/graph/analysis.py]
depends_on: ['[[feat-polyglot-engine]]', '[[feat-community-clustering]]', '[[plan-phase-4]]', '[[moc-features]]']
affects: ['[[feat-graph-report]]', '[[feat-wiki-export]]', '[[feat-agent-mcp]]']
last_verified: 2026-10-12
---

# Graph Topological Analysis Engine

## Purpose
Provides deep topological analysis over canonical property graphs to uncover architectural bottlenecks, unexpected cross-boundary links, and structural design risks.

## Behavior / Contract
- `god_nodes`: Computes degree centrality ranking for code entities while suppressing primitive type noise (`str`, `int`, etc.) and file containers.
- `surprising_connections`: Detects and scores edges crossing module, directory, language, or community boundaries with confidence weighting.
- `find_import_cycles`: Identifies circular dependency chains using elementary cycles and strongly connected components (SCC).
- `suggest_questions`: Synthesizes actionable architectural review questions for developers and AI agents.
- `graph_diff`: Calculates structural diffs (added, removed, modified nodes and edges) across graph versions.

## Impact
- **Depends on:** [[feat-polyglot-engine]], [[feat-community-clustering]], [[plan-phase-4]], [[moc-features]]
- **Affects:** [[feat-graph-report]], [[feat-wiki-export]], [[feat-agent-mcp]]

## Related
[[feat-community-clustering]], [[moc-features]]
