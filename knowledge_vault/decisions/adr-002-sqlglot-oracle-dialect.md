---
id: adr-002-sqlglot-oracle-dialect
type: decision
title: SQLGlot with Oracle Dialect for SQL Parsing
summary: Standardize on sqlglot with oracle dialect support as the deterministic SQL
  parser and table extractor.
status: accepted
tags: [architecture, sql, parser, adr]
affects: ['[[comp-parsers]]', '[[data-node-sqlquery]]', '[[feat-sql-parser]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 3"
depends_on: []
---
# ADR-002: SQLGlot with Oracle Dialect for SQL Parsing

## Status
Accepted

## Context
Enterprise codebases frequently contain complex SQL queries and scripts, often written in Oracle PL/SQL or dialect-specific syntax. The system needs reliable extraction of statement types, query text, and referenced database tables without sending SQL to an LLM.

## Decision
Adopt `sqlglot` as the deterministic SQL parser library, configuring `dialect="oracle"` by default while supporting other standard SQL dialects via configuration.

## Alternatives considered
- **python-sqlparse:** Good for tokenizing and formatting, but poor AST representation and fragile table extraction for complex joins or subqueries.
- **LLM-based SQL extraction:** Unreliable, non-deterministic, and consumes costly context tokens on large SQL migration files.
- **Oracle JDBC / database connectivity:** Requires live DB connection, credentials, and drivers; violates local standalone parsing rule.

## Consequences
- **Positive:** Pure Python; handles Oracle dialect nuances (merge statements, hints, package calls); extracts table AST nodes robustly; deterministic.
- **Negative:** Highly obscure or invalid proprietary PL/SQL blocks may fail AST generation and require fallback error logging.

## Notes
[[feat-sql-parser]], [[moc-decisions]]
