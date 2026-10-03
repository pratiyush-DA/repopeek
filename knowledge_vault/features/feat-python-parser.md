---
id: feat-python-parser
type: feature
title: Python Parser
summary: Mechanically extract function definitions, call relationships, imports, and embedded SQL from .py files via AST analysis with syntax-error fallback.
status: active
tags: [phase3, parser, deterministic]
code_refs: [repopeek/parsers/python.py, repopeek/parsers/base.py]
depends_on: ['[[adr-005-python-parser-tbd]]', '[[comp-parsers]]', '[[data-node-file]]',
  '[[data-node-function]]', '[[feat-file-classification]]', '[[req-deterministic-extraction]]']
affects: ['[[data-node-file]]', '[[data-node-function]]', '[[feat-graph-construction]]']
last_verified: 2026-10-03
source: "_sources/task_list.md §Phase 3"
---
# Python Parser

## Purpose
Produces the deterministic Python substrate of the graph. Every function, method, class, import, call, data access, and embedded SQL query is a fact extracted directly from source code without LLM invocation.

## Behavior / Contract
- **Input:** Source string or `.py` file path.
- **Outputs emitted as canonical NodeCards and Edges:**
  - `file` node per file with module docstring narrative and SHA-256 hash.
  - `class` node per `class` definition with inheritance bases, docstrings, and `INHERITS` edges.
  - `function` or `method` node per `def` / `async def` with exact line spans, signatures, docstrings, and cyclomatic complexity.
  - `IMPORTS` edges from file to imported modules/symbols.
  - `CALLS` edges from caller functions to invoked functions/methods with line evidence.
  - `RAISES` edges to raised exceptions.
  - `DEFINED_IN` edges anchoring functions and classes to parent lexical scopes.
  - `EMBEDS_SQL` edges and `sql_query` nodes for detected SQL query literals.
- **Resilient Fallback:** When `ast.parse` encounters `SyntaxError`, the parser shifts to line-by-line regex scanning (`FALLBACK_FUNC_RE`, `FALLBACK_CLASS_RE`, `FALLBACK_IMPORT_RE`), producing partial nodes flagged with `confidence="unresolved"` so broken files never crash repo crawls.

## Impact (blast radius)
- **Depends on:** [[feat-file-classification]], [[req-deterministic-extraction]]
- **Affects (downstream):** [[feat-graph-construction]], [[data-node-function]], [[data-node-file]], [[data-edge-types]]
- **If this changes, also review:** [[con-determinism]], [[adr-005-python-parser-tbd]]

## Related
[[moc-features]]
