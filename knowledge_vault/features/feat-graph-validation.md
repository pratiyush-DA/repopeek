---
id: feat-graph-validation
type: feature
title: Graph Validation
summary: Validate the in-memory property graph against schema definitions to ensure
  node and edge integrity.
status: planned
tags: [phase4, validation, schema]
code_refs: [repopeek/graph/]
depends_on: ['[[comp-graph]]', '[[data-edge-types]]', '[[feat-graph-construction]]']
affects: ['[[feat-graph-persistence]]', '[[feat-semantic-enrichment]]']
last_verified: 2026-10-03
source: _sources/graph_schema.md
---
# Graph Validation

## Purpose
Enforces strict structural and schema invariants on the property graph prior to persistence or semantic enrichment, preventing malformed graphs, missing required fields, or illegal edge connections.

## Behavior / Contract
- Input: In-memory NetworkX graph instance
- Reference Schema: Governed by `docs/graph_schema.json` and defined in [[data-edge-types]] and data node notes
- Validations:
  - Every node must have a valid `id`, recognized `type`, and mandatory attributes (e.g. `filepath` for files/functions)
  - Edge endpoints must exist within the graph (no dangling edges)
  - Edge types must be within allowed set: `DEFINED_IN`, `CALLS`, `IMPORTS`, `READS`, `IMPLEMENTS`
- Failure Mode: Raises validation exceptions or returns diagnostic report detailing violating node and edge IDs.

## Impact (blast radius)
- **Depends on:** [[feat-graph-construction]], [[comp-graph]]
- **Affects (downstream):** [[feat-semantic-enrichment]], [[feat-graph-persistence]]
- **If this changes, also review:** [[data-edge-types]], [[req-deterministic-extraction]], [[con-determinism]]

## Related
[[moc-features]], [[moc-data-models]]
