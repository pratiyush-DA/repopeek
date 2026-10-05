---
id: comp-parsers
type: component
title: Parsers Component
summary: Module repopeek/parsers/ providing deterministic AST and dialect parsers
  for Python, SQL, and JSON files.
status: active
tags: [phase3, component, parsers]
code_refs: [repopeek/parsers/base.py, repopeek/parsers/python.py, repopeek/parsers/sql.py, repopeek/parsers/shell.py, repopeek/parsers/config.py, repopeek/parsers/typescript.py, repopeek/parsers/__init__.py]
depends_on: ['[[adr-002-sqlglot-oracle-dialect]]', '[[adr-005-python-parser-tbd]]',
  '[[comp-discovery]]', '[[con-determinism]]', '[[con-local-execution]]', '[[con-scope-languages]]',
  '[[data-node-function]]', '[[data-node-jsonconfig]]', '[[data-node-sqlquery]]',
  '[[req-deterministic-extraction]]', '[[res-parsing-stack]]']
affects: ['[[comp-graph]]', '[[feat-json-parser]]', '[[feat-python-parser]]', '[[feat-sql-parser]]', '[[feat-typescript-parser]]']
last_verified: 2026-10-05
source: "_sources/task_list.md §Phase 3"
---
# Parsers Component

## Purpose
Encapsulates all deterministic code parsing engines. Translates source code files into structured intermediate AST representations, extracting functions, imports, calls, SQL statements, and table references without any LLM reliance.

## Responsibilities
- Parse Python source code to extract definitions, decorators, call sites, data reads/writes, and module imports.
- Parse SQL scripts using SQLGlot (Oracle dialect) to extract AST, query text, statements, and referenced tables.
- Parse JSON configuration files to extract top-level keys and structure.
- Emit uniform parsed node and edge representations for graph ingestion.

## Interface / Contract
- `BaseParser.parse_source(source: str, rel_path: str) -> ParseResult`
- `BaseParser.parse_file(file_path: Path, repo_root: Optional[Path]) -> ParseResult`
- `PythonParser.parse_source(...) -> ParseResult`
- Inputs: Validated source strings and file paths
- Outputs: `ParseResult` dataclass containing discovered `NodeCard`s and `Edge`s
- Errors: Captures syntax and parsing errors gracefully in `errors` list attribute.

## Impact (blast radius)
- **Depends on:** [[comp-discovery]], [[req-deterministic-extraction]]
- **Affects (downstream):** [[comp-graph]], [[feat-python-parser]], [[feat-sql-parser]], [[feat-json-parser]]
- **If this changes, also review:** [[adr-002-sqlglot-oracle-dialect]], [[adr-005-python-parser-tbd]], [[con-determinism]]
- **Data touched:** [[data-node-file]], [[data-node-function]], [[data-node-sqlquery]], [[data-node-jsonconfig]]

## Decisions & Constraints
[[adr-002-sqlglot-oracle-dialect]], [[adr-005-python-parser-tbd]], [[con-determinism]]

## Related
[[moc-architecture]]
