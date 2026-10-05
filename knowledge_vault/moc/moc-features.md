---
id: moc-features
type: moc
title: "Features \u2014 Map of Content"
summary: Hub for all end-user and agent-facing capabilities in Repopeek.
last_verified: 2026-10-03
affects: ['[[plan]]']
depends_on: []
---
# Features — Map of Content

> Hub note only. No content of its own.

## Discovery & classification

- [[feat-file-discovery]] — recursively traverse a repo to find candidate files
- [[feat-file-classification]] — classify files as Python / SQL / JSON

## Deterministic parsing

- [[feat-python-parser]] — AST extraction: functions, calls, imports
- [[feat-sql-parser]] — SQL query and table extraction (Oracle PL/SQL capable)
- [[feat-json-parser]] — config key structure extraction

## Graph

- [[feat-graph-construction]] — build unified NetworkX property graph
- [[feat-graph-validation]] — validate graph against schema at build time
- [[feat-graph-persistence]] — export graph to local JSON (or SQLite — TBD)

## Semantic layer

- [[feat-semantic-enrichment]] — LLM pipeline: function → module → BusinessProcess/Story
- [[feat-provenance-binding]] — attach file path, line range, confidence to semantic nodes

## Agent interface

- [[feat-query-cli]] — inspect nodes, traverse CALLS/READS chains, find impact trees
- [[feat-intent-retrieval]] — resolve natural language tasks to candidate symbols via AST + FTS5 BM25 + RRF
- [[feat-traversal-confidence]] — mathematical traversal confidence, multi-path reinforcement, and blast radius partitioning

## Related

- [[moc-architecture]]
- [[moc-data-models]]
