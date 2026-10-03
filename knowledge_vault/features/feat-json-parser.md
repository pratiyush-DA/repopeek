---
id: feat-json-parser
type: feature
title: JSON Parser
summary: Parse configuration JSON files into graph nodes, extracting top-level keys
  and structure without LLM inference.
status: planned
tags: [phase3, parser, deterministic]
code_refs: [repopeek/parsers/]
depends_on: ['[[comp-parsers]]', '[[data-node-file]]', '[[data-node-jsonconfig]]',
  '[[feat-file-classification]]', '[[req-deterministic-extraction]]']
affects: ['[[data-node-jsonconfig]]', '[[feat-graph-construction]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 3"
---
# JSON Parser

## Purpose
Deterministically ingests structured JSON configuration files into the property graph, capturing structural metadata and configuration schema without interpretation or hallucination.

## Behavior / Contract
- Input: `.json` file path identified by [[feat-file-classification]]
- Output:
  - `JsonConfig` node with `id`, `filepath`, and top-level `keys` array
  - `DEFINED_IN` edge connecting `JsonConfig` node to its parent `File` node
- Error Handling: Invalid JSON files log a parser warning and are recorded with parse failure status rather than halting traversal.
- Deterministic: Same JSON input yields identical graph node properties and keys.

## Impact (blast radius)
- **Depends on:** [[feat-file-classification]], [[req-deterministic-extraction]]
- **Affects (downstream):** [[feat-graph-construction]], [[data-node-jsonconfig]], [[data-edge-types]]
- **If this changes, also review:** [[con-determinism]], [[con-scope-languages]]

## Related
[[moc-features]]
