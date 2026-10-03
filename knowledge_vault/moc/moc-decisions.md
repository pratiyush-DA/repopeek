---
id: moc-decisions
type: moc
title: "Decisions \u2014 Map of Content"
summary: Hub for all Architecture Decision Records (ADRs) in Repopeek.
last_verified: 2026-10-03
affects: []
depends_on: []
---
# Decisions — Map of Content

> Hub note only. No content of its own.

## Accepted decisions

- [[adr-001-networkx-local-graph]] — Use NetworkX (not Neo4j) as graph library for MVP
- [[adr-002-sqlglot-oracle-dialect]] — Use sqlglot with Oracle dialect as primary SQL parser
- [[adr-003-no-distributed-infra]] — Prohibit all distributed infrastructure for MVP

## Pending decisions (TBD — need input)

- [[adr-004-graph-persistence-tbd]] — Graph output format: JSON vs SQLite
- [[adr-005-python-parser-tbd]] — Python parsing: tree-sitter vs stdlib `ast`

## Constraints enforced by decisions

- [[con-no-distributed-graph]]
- [[con-no-cloud-saas]]
- [[con-scope-languages]]

## Open questions

- [[moc-open-questions]]
