---
id: plan-phase-4
type: plan
title: Phase 4 Execution Plan — Universal Polyglot Engine & Full Graphify Parity
summary: Implementation roadmap for Phase 4 achieving 36+ language coverage, topological graph analysis, Louvain/Leiden clustering, and agent wiki/report exports.
status: active
tags: [phase4, planning, architecture, polyglot, graphify]
code_refs: [repopeek/discovery/classifier.py, repopeek/parsers/polyglot.py, repopeek/graph/analysis.py, repopeek/graph/clustering.py, repopeek/export/report.py, repopeek/export/wiki.py, repopeek/export/html.py, repopeek/cli.py]
depends_on: ['[[moc-architecture]]', '[[moc-features]]']
affects: ['[[log-phase-4]]', '[[feat-polyglot-engine]]', '[[feat-graph-analysis]]', '[[feat-community-clustering]]', '[[feat-wiki-export]]', '[[feat-graph-report]]']
last_verified: 2026-10-12
---

# Phase 4 Execution Plan — Universal Polyglot Engine & Full Graphify Parity

## 1. Executive Summary & Objective
Phase 4 scales RepoPeek from its initial 7-language foundation (Python, SQL, Shell, JSON, YAML, TypeScript, JavaScript) to full universal polyglot coverage of 36+ programming languages with complete feature parity to Graphify (v8):
1. **Universal Polyglot Tree-Sitter Engine**: Declarative AST extraction with graceful regex fallback across 36+ languages and sensitive file shielding.
2. **Graph Topological Analysis Engine**: God nodes ranking, surprising cross-community connections, import cycle detection, and automated architectural prompts.
3. **Unsupervised Community Clustering**: Louvain / Leiden graph partitioning, cohesion scoring ($0.0 \dots 1.0$), and semantic community labeling.
4. **Knowledge Artifacts & Exporters**: Comprehensive `GRAPH_REPORT.md` audit trail, Wikipedia-style Markdown Agent Wiki (`wiki/index.md` + per-community and hub node deep dives), standalone interactive HTML visualizer, and multi-format exports.
5. **Multi-Agent Skill Packaging**: Agent skill definitions for Antigravity, Claude Code, Cursor, and Codex.

## 2. Delivery Components
- **Component 1: Discovery & Classification Expansion (`repopeek/discovery/classifier.py`, `crawler.py`):** 36+ file extensions mapped, sensitive file shielding.
- **Component 2: Universal Polyglot Parser Engine (`repopeek/parsers/polyglot.py`):** `LanguageConfig` dataclass, `PolyglotTreeSitterParser` with dual-tier tree-sitter AST and regex fallback.
- **Component 3: Graph Topological Analysis Engine (`repopeek/graph/analysis.py`):** `god_nodes`, `surprising_connections`, `find_import_cycles`, `suggest_questions`, and `graph_diff`.
- **Component 4: Community Detection & Clustering Engine (`repopeek/graph/clustering.py`):** `detect_communities`, `compute_cohesion_scores`, `generate_community_labels`.
- **Component 5: Rich Reporting & Agent Wiki (`repopeek/export/`):** `generate_graph_report`, `export_wiki`, `export_html`.
- **Component 6: CLI & MCP Server Integration (`repopeek/cli.py`, `repopeek/query/mcp_server.py`):** subcommands `report`, `wiki`, `cluster`, `analyze`, `export`, and new MCP tools.

## 3. Execution Tracking
Execution milestones and verification results are tracked in [[log-phase-4]].
