---
id: adr-008-canonical-graph-lenses
type: decision
title: Canonical Property Graph with Materialised Lens Graphs
summary: Maintain a single canonical typed property graph with stable IDs and materialise
  specialized lens graphs for low-context consumption.
status: accepted
tags: [architecture, graph, schema, lenses, adr]
code_refs: [repopeek/graph/]
depends_on: ['[[res-prior-art]]']
affects: ['[[comp-graph]]', '[[data-graph-lenses]]', '[[data-node-card-spec]]', '[[moc-data-models]]',
  '[[moc-decisions]]']
last_verified: 2026-10-03
source: "RepoPeek Owner Briefing \xA72 & \xA75"
---
# ADR-008: Canonical Property Graph with Materialised Lens Graphs

## Status
Accepted

## Context
Downstream AI agents operate within tight context windows (a few hundred tokens). If an agent needs to reason about call paths, it should not be burdened with intra-function AST variables, SQL DDL details, or environment configs. Conversely, building ten disjoint schemas risks divergence and duplicate parsing.

## Decision
1. **Single Canonical Store:** Ingest all parsed facts into a single, unified directed property multigraph.
2. **Stable Node IDs:** Deterministic URI-style IDs resistant to formatting changes:
   `<lang>:<repo-relative-path>::<qualified.name>` (e.g. `py:repopeek/config.py::RepopeekConfig.from_json_file`).
3. **Materialised Lens Views:** Materialise specialized, bounded subgraphs as standalone JSON artifacts:
   - Module/File Lens
   - Symbol/Containment Lens
   - Call Graph Lens
   - Class/Inheritance Lens
   - Data & Variable Def-Use Lens
   - Data-Entity (SQL/Table/Config) Lens
   - Environment & Secrets-by-Name Lens
   - Process & Shell Script Lens
   - Exception Flow Lens
   - Test-to-Code Lens
   - Cross-Language Bridges (Python to SQL, Shell to Python)
4. **Minimal Node Cards:** Queries return compact JSON node cards (<50–100 tokens each) containing signature, span, facts summary, one-line story, and provenance.

## Consequences
- Single ingestion pipeline; downstream consumers load only the precise lens needed.

## Notes
[[moc-data-models]], [[moc-decisions]]
