---
id: moc-data-models
type: moc
title: "Data Models \u2014 Map of Content"
summary: Hub for all graph node types, edge types, and schema contracts in Repopeek.
last_verified: 2026-10-03
affects: ['[[data-edge-types]]', '[[data-node-businessprocess]]', '[[data-node-file]]',
  '[[data-node-function]]', '[[data-node-jsonconfig]]', '[[data-node-repository]]',
  '[[data-node-sqlquery]]', '[[data-node-story]]']
depends_on: []
---
# Data Models — Map of Content

> Hub note only. No content of its own.

## Deterministic nodes

- [[data-node-repository]] — root codebase node
- [[data-node-file]] — physical file on disk
- [[data-node-function]] — parsed function or method
- [[data-node-sqlquery]] — extracted SQL statement
- [[data-node-jsonconfig]] — configuration file or object

## Semantic nodes

- [[data-node-businessprocess]] — LLM-inferred business workflow node
- [[data-node-story]] — LLM-inferred narrative of how code achieves a goal

## Edge types

- [[data-edge-types]] — DEFINED\_IN, CALLS, IMPORTS, READS, IMPLEMENTS

## Related

- [[feat-graph-construction]]
- [[feat-graph-validation]]
- [[moc-architecture]]
