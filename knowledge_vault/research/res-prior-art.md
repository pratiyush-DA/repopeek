---
id: res-prior-art
type: research
title: "Prior Art Analysis \u2014 Code Knowledge Graphs and Agent Exploration"
summary: Critical evaluation of Codebase-Memory (arXiv 2603.27277), CodeGraphContext,
  RepoGraph, and CodexGraph.
status: completed
tags: [research, prior-art, knowledge-graphs, mcp, agents]
code_refs: []
depends_on: ['[[plan]]']
affects: ['[[adr-008-canonical-graph-lenses]]', '[[adr-011-mcp-interface]]']
last_verified: 2026-10-03
---
# Prior Art Analysis — Code Knowledge Graphs and Agent Exploration

## Overview
Recent research and open-source tooling have recognized that raw file-reading and grep workflows are too token-expensive for autonomous coding agents. This note evaluates current state of the art to avoid reinventing wheels while addressing their critical gaps for our low-context consumer.

## Evaluated Systems

### 1. Codebase-Memory (arXiv:2603.27277)
- **Primary Source:** Lavaee et al., *Codebase-Memory: Tree-Sitter-Based Knowledge Graphs for LLM Code Exploration via MCP* (2026).
- **Architecture:** Tree-sitter AST parsing stored in a local SQLite file, exposed as an MCP server with 14–17 query tools.
- **Strengths:** Single static binary, no external DB/Docker, claims up to 120x token reduction for structural discovery (call traces, definitions).
- **Gaps for RepoPeek:** Focuses purely on raw AST facts. Lacks business process understanding, user stories, cross-language bridges (e.g. Python to SQL table flow), and multi-lens materialisation.

### 2. CodeGraphContext (CGC)
- **Architecture:** Combines Tree-sitter and SCIP indexing to build a graph database (Neo4j or FalkorDB), exposed via CLI and MCP.
- **Strengths:** Strong relational traversal and cross-file reference mapping.
- **Gaps for RepoPeek:** Requires external server daemons (Neo4j/FalkorDB), directly violating our local-only, zero-distributed-infra constraint ([[adr-003-no-distributed-infra]], [[con-no-distributed-graph]]).

### 3. RepoGraph & CodexGraph
- **RepoGraph (ICLR/NeurIPS literature):** Employs graph neural networks or heuristic subgraphs to guide LLM code generation.
- **CodexGraph:** Maps repository structure to a knowledge graph for semantic navigation.
- **Gaps:** Often treat the graph as a monolithic vector/embedding store or black-box embedding index rather than an inspectable property graph with verifiable line-level provenance.

## RepoPeek Differentiation

| Capability | Codebase-Memory | CodeGraphContext | RepoPeek |
|---|---|---|---|
| **Storage Engine** | SQLite binary | Neo4j / FalkorDB | Canonical JSON + optional SQLite cache |
| **Parsing Stack** | Tree-sitter only | Tree-sitter + SCIP | Tree-sitter + stdlib AST + SQLGlot + Bash |
| **Output Model** | Monolithic DB queries | Graph database | Multi-Lens Graphs (Class, Call, Data, Config) |
| **Semantic Overlay** | None (pure AST) | Minimal | Grounded Stories & Business Processes |
| **Provenance** | File + line | File + line | File, line, AST node IDs, commit SHA, confidence |
| **Context Optimization** | Ad-hoc query tools | Tool responses | Budget-governed Context-Packs (<500 tokens) |
| **Local / Standalone** | Yes (binary) | No (daemon required) | Yes (100% local Python CLI / MCP) |

## Conclusion
RepoPeek takes the local simplicity of Codebase-Memory and the rich relational depth of CodeGraphContext, while introducing multi-lens views, cost-controlled semantic stories, and compact context-packs specifically designed for small context-window consumers.
