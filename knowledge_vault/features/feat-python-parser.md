---
id: feat-python-parser
type: feature
title: Python Parser
summary: Mechanically extract function definitions, call relationships, and imports
  from .py files via AST analysis; no LLM involved.
status: planned
tags: [phase3, parser, deterministic]
code_refs: [repopeek/parsers/]
depends_on: ['[[adr-005-python-parser-tbd]]', '[[comp-parsers]]', '[[data-node-file]]',
  '[[data-node-function]]', '[[feat-file-classification]]', '[[req-deterministic-extraction]]']
affects: ['[[data-node-file]]', '[[data-node-function]]', '[[feat-graph-construction]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 3"
---
# Python Parser

## Purpose
Produces the deterministic Python substrate of the graph. Every function, import, and call is a fact extracted from source code, not inferred.

## Behavior / Contract
- Input: `.py` file path
- Outputs emitted as graph nodes/edges:
  - `File` node per file
  - `Function` node per `def` / `async def` with `start_line`, `end_line`
  - `IMPORTS` edges from file to its imports
  - `CALLS` edges where one function calls another (best-effort — unresolved calls are omitted, not guessed)
  - `DEFINED_IN` edge from each `Function` to its `File`
- Parser library: **TBD** — see [[adr-005-python-parser-tbd]]

## Impact (blast radius)
- **Depends on:** [[feat-file-classification]], [[req-deterministic-extraction]]
- **Affects (downstream):** [[feat-graph-construction]], [[data-node-function]], [[data-node-file]], [[data-edge-types]]
- **If this changes, also review:** [[con-determinism]], [[adr-005-python-parser-tbd]]

## Open questions
- Parser library (tree-sitter vs stdlib `ast`) — see [[adr-005-python-parser-tbd]]

## Related
[[moc-features]]
