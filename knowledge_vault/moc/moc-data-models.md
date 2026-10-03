---
id: moc-data-models
type: moc
title: "Data Models \u2014 Map of Content"
summary: Hub for all graph node types, edge types, node-card specs, and lens definitions
  in Repopeek.
last_verified: 2026-10-03
affects: ['[[data-edge-types]]', '[[data-graph-lenses]]', '[[data-node-businessprocess]]',
  '[[data-node-card-spec]]', '[[data-node-file]]', '[[data-node-function]]', '[[data-node-jsonconfig]]',
  '[[data-node-repository]]', '[[data-node-sqlquery]]', '[[data-node-story]]']
depends_on: ['[[adr-008-canonical-graph-lenses]]']
---
# Data Models — Map of Content

> Hub note for graph schemas, edge taxonomy, node cards, and lens projections.

## Consumer Payloads
- [[data-node-card-spec]] — atomic node card schema (<80 tokens) for low-context agents
- [[data-graph-lenses]] — catalogue of 11 specialized lens graphs derived from canonical store

## Deterministic Node Types
- [[data-node-repository]] — root codebase node
- [[data-node-file]] — physical file on disk
- [[data-node-function]] — parsed function or method
- [[data-node-sqlquery]] — extracted SQL statement
- [[data-node-jsonconfig]] — configuration file or object

## Semantic Node Types
- [[data-node-businessprocess]] — business workflow synthesized by LLM
- [[data-node-story]] — functional goal story grounded in AST facts

## Edge Taxonomy
- [[data-edge-types]] — DEFINED_IN, CALLS, IMPORTS, READS, IMPLEMENTS, and lens-specific bridges

## Architectural Foundation
- [[adr-008-canonical-graph-lenses]] — canonical property graph and materialised lenses
- [[feat-graph-construction]]
- [[feat-graph-validation]]
- [[moc-architecture]]
