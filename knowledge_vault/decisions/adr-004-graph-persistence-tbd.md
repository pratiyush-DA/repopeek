---
id: adr-004-graph-persistence-tbd
type: decision
title: Graph Persistence Format (Pending Decision)
summary: Evaluate JSON file serialization vs SQLite storage for local graph persistence;
  decision currently TBD.
status: proposed
tags: [architecture, storage, open-question, adr]
affects: ['[[comp-graph]]', '[[feat-graph-persistence]]', '[[moc-open-questions]]']
last_verified: 2026-10-03
source: "_sources/architecture_documentation.md \xA7Phase 4"
depends_on: []
---
# ADR-004: Graph Persistence Format (Pending Decision)

## Status
Proposed (Pending Decision)

## Context
When persisting the NetworkX property graph to disk, two main local formats are viable: a standardized JSON file (using NetworkX node-link format) or a lightweight single-file SQLite database.

## Decision
Decision is currently marked **TBD**. For initial Phase 1/4 prototypes, JSON serialization (`graph.json`) is the default baseline format, but SQLite remains an active candidate if JSON parsing overhead becomes prohibitive on larger repositories.

## Alternatives considered
- **JSON Node-Link Format:**
  - *Pros:* Human-readable; trivially inspectable with jq or text editors; built-in NetworkX `node_link_data` / `node_link_graph` support.
  - *Cons:* Must load the entire file into memory at once; slow for graphs with >100k nodes.
- **SQLite Database:**
  - *Pros:* Fast indexed queries; can read subsets without loading full graph; standard single-file format.
  - *Cons:* Requires custom schema mapping and relational translation; not plain text inspectable.

## Consequences
- Requires tracking as an open architectural question before final Phase 4 completion.

## Notes
[[feat-graph-persistence]], [[moc-open-questions]], [[moc-decisions]]
