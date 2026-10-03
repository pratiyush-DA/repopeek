---
id: feat-sql-parser
type: feature
title: SQL Parser
summary: Extract SQL queries, table definitions, and referenced tables/columns from .sql files using sqlglot with Oracle dialect default and ANSI/Postgres fallback.
status: active
tags: [phase4, parser, deterministic, sql, oracle]
code_refs: [repopeek/parsers/sql.py]
depends_on: ['[[adr-002-sqlglot-oracle-dialect]]', '[[comp-parsers]]', '[[data-node-file]]',
  '[[data-node-sqlquery]]', '[[feat-file-classification]]', '[[req-deterministic-extraction]]']
affects: ['[[data-node-file]]', '[[data-node-sqlquery]]', '[[feat-graph-construction]]']
last_verified: 2026-10-03
source: "_sources/task_list.md §Phase 4"
---
# SQL Parser

## Purpose
Produces the deterministic SQL substrate of the graph. Extracts queries and table references mechanically. Handles Oracle PL/SQL syntax without fabricating table names for dynamic SQL it cannot resolve.

## Behavior / Contract
- Input: `.sql` file path
- Outputs:
  - `File` node per file
  - `SQLQuery` node per extractable statement with `query_text`
  - `DEFINED_IN` edge from `SQLQuery` to its `File`
  - Table references captured as metadata on `SQLQuery` nodes
- Parser: `sqlglot` with `dialect="oracle"` (see [[adr-002-sqlglot-oracle-dialect]])
- PL/SQL constructs handled:
  - `EXCEPTION WHEN OTHERS THEN` blocks — parsed without breaking statement boundaries
  - `||` string concatenation in dynamic SQL — tokenized; unresolvable table names marked as dynamic (not omitted)
  - `EXECUTE IMMEDIATE` with string literals — best-effort table extraction
- Unresolvable dynamic table names: emit a node with `table_name: "<dynamic>"` rather than guessing.

## Impact (blast radius)
- **Depends on:** [[feat-file-classification]], [[req-deterministic-extraction]]
- **Affects (downstream):** [[feat-graph-construction]], [[data-node-sqlquery]], [[data-edge-types]]
- **If this changes, also review:** [[adr-002-sqlglot-oracle-dialect]], [[con-determinism]]

## Decisions & Constraints
[[adr-002-sqlglot-oracle-dialect]], [[con-determinism]]

## Related
[[moc-features]]
