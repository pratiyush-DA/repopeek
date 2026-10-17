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
last_verified: 2026-10-17
---

# Graph Topological Analysis Engine

## Purpose
Provides deep topological analysis over canonical property graphs to uncover architectural bottlenecks, unexpected cross-boundary links, and structural design risks.

## Behavior / Contract
- `god_nodes`: Computes degree centrality ranking for code entities while suppressing external library nodes (`ext:*`), unresolved symbols, primitive builtins (`len`, `range`, `print`), and file containers.
- `surprising_connections`: Detects and scores edges crossing module, directory, language, or community boundaries with confidence weighting.
- `find_import_cycles`: Identifies circular dependency chains strictly restricted to `EdgeType.IMPORTS` between code files (excluding non-code files and call/inheritance edges).
- `suggest_questions`: Synthesizes actionable architectural review questions for developers and AI agents.
- `graph_diff`: Calculates structural diffs (added, removed, modified nodes and edges) across graph versions.

## Impact
- **Depends on:** [[feat-polyglot-engine]], [[feat-community-clustering]], [[plan-phase-4]], [[moc-features]]
- **Affects:** [[feat-graph-report]], [[feat-wiki-export]], [[feat-agent-mcp]]

## Related
[[feat-community-clustering]], [[moc-features]]
