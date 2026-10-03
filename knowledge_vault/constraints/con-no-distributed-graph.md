---
id: con-no-distributed-graph
type: constraint
title: Prohibition of Distributed Graph Databases
summary: Repopeek must never depend on or connect to external distributed graph databases
  like Neo4j or Memgraph.
status: active
tags: [constraint, scope, architecture]
affects: ['[[adr-001-networkx-local-graph]]', '[[adr-003-no-distributed-infra]]',
  '[[comp-graph]]']
last_verified: 2026-10-03
source: "_sources/cursorrules.md \xA7Scope Protection"
depends_on: ['[[adr-001-networkx-local-graph]]', '[[adr-003-no-distributed-infra]]']
---
# Prohibition of Distributed Graph Databases

## Rule
Repopeek must strictly use local in-memory or single-file embedded graph storage (e.g. NetworkX, JSON, or SQLite). It must NEVER connect to, require, or bundle distributed graph databases such as Neo4j, Memgraph, TigerGraph, or Amazon Neptune.

## Rationale
Prevents operational complexity, daemon requirements, network dependencies, and license entanglements. Repopeek is designed to be an easily installed, local developer tool.

## What it prohibits
- Adding Neo4j/Memgraph Python client drivers or dependencies.
- Requiring Docker containers or background daemon processes to run graph queries.
- Writing Cypher queries that assume an external server runtime.

## Enforcement
- Code review and dependency checking: verify `pyproject.toml` contains only local embedded libraries.

## Related
[[adr-001-networkx-local-graph]], [[adr-003-no-distributed-infra]], [[moc-decisions]]
