---
id: feat-query-cli
type: feature
title: Query CLI
summary: Command-line interface allowing developers and agents to query graph nodes,
  inspect dependencies, and compute impact trees.
status: planned
tags: [phase6, query, cli]
code_refs: [repopeek/query/, repopeek/cli.py]
depends_on: ['[[adr-011-mcp-interface]]', '[[comp-cli]]', '[[comp-graph]]', '[[comp-query]]',
  '[[data-node-card-spec]]', '[[feat-graph-construction]]', '[[feat-graph-persistence]]',
  '[[req-queryable-graph]]']
affects: ['[[comp-cli]]', '[[comp-query]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 6"
---
# Query CLI

## Purpose
Provides an intuitive command-line interface for human developers and autonomous AI agents to explore the intelligence graph, trace call hierarchies, discover table dependencies, and determine blast radius of changes.

## Behavior / Contract
- Commands:
  - `repopeek inspect <node-id>`: Print node properties, inward edges, and outward edges
  - `repopeek trace <function-name>`: Display forward or reverse CALLS chains
  - `repopeek impact <file-path>`: Calculate transitive impact tree for code or schema changes
  - `repopeek processes`: List synthesized business processes with their implementing code references
- Output Formats: Formatted human-readable terminal tree, or machine-readable JSON for agent consumption (`--json` flag).

## Impact (blast radius)
- **Depends on:** [[feat-graph-persistence]], [[comp-graph]], [[req-queryable-graph]]
- **Affects (downstream):** [[comp-query]], [[comp-cli]]
- **If this changes, also review:** [[req-mvp-success-criteria]]

## Related
[[moc-features]], [[moc-architecture]]
