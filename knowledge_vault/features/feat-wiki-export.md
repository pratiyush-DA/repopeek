---
id: feat-wiki-export
type: feature
title: Wikipedia-Style Markdown Agent Wiki Exporter
summary: Exports repository property graphs as an agent-crawlable Wikipedia-style Markdown documentation wiki with index.md, community articles, and god node deep dives.
status: active
tags: [phase4, wiki, export, documentation, agent-crawlable]
code_refs: [repopeek/export/wiki.py]
depends_on: ['[[feat-community-clustering]]', '[[feat-graph-analysis]]', '[[plan-phase-4]]', '[[moc-features]]']
affects: ['[[feat-graph-persistence]]', '[[feat-query-cli]]']
last_verified: 2026-10-12
---

# Wikipedia-Style Markdown Agent Wiki Exporter

## Purpose
Generates a lightweight, token-efficient Markdown wiki under `repopeek-out/wiki/` designed for low-context navigation by autonomous coding agents and human developers.

## Behavior / Contract
- `export_wiki`: Produces:
  - `wiki/index.md`: Master catalog with summary metrics, community table, and hub node rankings.
  - `wiki/community_<id>_<slug>.md`: Per-community articles with member tables, file citations, and cross-community couplings.
  - `wiki/god_<slug>.md`: Deep-dive articles for high-centrality symbols detailing inbound callers and outbound invocations.
- Portable relative Markdown links (`[label](slug.md)`) for crawlability.
- Windows MAX_PATH and filesystem safe slug generation.

## Impact
- **Depends on:** [[feat-community-clustering]], [[feat-graph-analysis]], [[plan-phase-4]], [[moc-features]]
- **Affects:** [[feat-graph-persistence]], [[feat-query-cli]]

## Related
[[feat-graph-report]], [[moc-features]]
