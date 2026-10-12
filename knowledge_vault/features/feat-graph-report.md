---
id: feat-graph-report
type: feature
title: Markdown Graph Report Generator
summary: Generates GRAPH_REPORT.md human and agent audit trails with metrics, top god nodes, community clusters, surprising edges, and cycle audits.
status: active
tags: [phase4, report, audit, markdown]
code_refs: [repopeek/export/report.py]
depends_on: ['[[feat-graph-analysis]]', '[[feat-community-clustering]]', '[[plan-phase-4]]', '[[moc-features]]']
affects: ['[[feat-query-cli]]', '[[feat-agent-mcp]]']
last_verified: 2026-10-12
---

# Markdown Graph Report Generator

## Purpose
Generates a comprehensive `GRAPH_REPORT.md` audit report summarizing graph metrics, architecture health, high-impact bottlenecks, and architectural recommendations.

## Behavior / Contract
- `generate_graph_report`:
  - Executive summary metrics table (total files, nodes, edges, communities, cycles).
  - Language breakdown (files and entities per language).
  - Top God Nodes table with degree centrality, complexity, and line citations.
  - Modular communities table with cohesion scores and member counts.
  - Surprising Connections table highlighting non-obvious couplings.
  - Circular dependency chains audit table with warning badges.
  - Automated architectural review questions.

## Impact
- **Depends on:** [[feat-graph-analysis]], [[feat-community-clustering]], [[plan-phase-4]], [[moc-features]]
- **Affects:** [[feat-query-cli]], [[feat-agent-mcp]]

## Related
[[feat-wiki-export]], [[moc-features]]
