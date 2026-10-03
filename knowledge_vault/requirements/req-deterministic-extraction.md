---
id: req-deterministic-extraction
type: requirement
title: Deterministic Code Relationship Extraction
summary: All structural code relationships (calls, imports, reads) must be extracted
  mechanically via static analysis, never via an LLM.
status: in-progress
tags: [mvp, determinism, core]
code_refs: [repopeek/parsers/]
depends_on: ['[[con-determinism]]']
affects: ['[[comp-parsers]]', '[[feat-graph-construction]]', '[[feat-json-parser]]',
  '[[feat-python-parser]]', '[[feat-sql-parser]]', '[[req-mvp-success-criteria]]',
  '[[req-provenance]]', '[[req-queryable-graph]]', '[[req-semantic-enrichment]]']
last_verified: 2026-10-03
source: "_sources/architecture_documentation.md \xA71 Deterministic Layer"
---
# Deterministic Code Relationship Extraction

## Purpose
The substrate layer of the graph must be a ground-truth, reproducible representation of facts extracted mechanically from source code. An LLM must never invent or modify structural relationships.

## Behavior / Contract
- Same input at the same commit → identical deterministic graph output every time.
- Extracted relationships: `CALLS`, `IMPORTS`, `READS`, `DEFINED_IN`.
- Extracted node types: `File`, `Function`, `SQLQuery`, `JSONConfig`.
- If a fact cannot be extracted statically, it is either omitted or marked TBD; never guessed.

## Impact (blast radius)
- **Depends on:** [[feat-file-classification]]
- **Affects (downstream):** [[feat-python-parser]], [[feat-sql-parser]], [[feat-json-parser]], [[feat-graph-construction]]
- **If this changes, also review:** [[con-determinism]], [[con-no-hallucination]], [[data-edge-types]]

## Decisions & Constraints
[[con-determinism]], [[con-no-hallucination]], [[adr-005-python-parser-tbd]]

## Related
[[moc-features]]
