---
id: adr-004-graph-persistence-tbd
type: decision
title: Canonical JSON Persistence with Optional SQLite Traversal Cache
summary: Use deterministic sharded JSON as the canonical persistence format, with
  an optional derived SQLite index for fast recursive traversal.
status: accepted
tags: [architecture, storage, json, sqlite, adr]
code_refs: [repopeek/graph/]
depends_on: []
affects: ['[[comp-graph]]', '[[feat-graph-persistence]]', '[[moc-decisions]]', '[[moc-open-questions]]']
last_verified: 2026-10-03
source: "RepoPeek Owner Briefing \xA72 & \xA77"
---
# ADR-004: Canonical JSON Persistence with Optional SQLite Traversal Cache

## Status
Accepted (Owner Approved)

## Context
RepoPeek requires a persistent on-disk format for the canonical property graph and materialised lenses. The format must be fast, deterministic (identical code yields byte-identical artifacts for clean git diffs), inspectable, and support low-context reading without loading entire giant monolithic files into memory.

## Decision
1. **Canonical Format: Sharded JSON.** Machine data must use JSON (never YAML, which is slower to parse, memory-heavy, and type-ambiguous).
2. **Determinism:** All JSON serializers must enforce sorted keys, stable array ordering, and omit timestamps from content-hashed blobs.
3. **Layout:** Sharded hierarchy: one JSON file per source file containing its node cards and edges, plus lens index manifests.
4. **Optional SQLite Cache:** A disposable SQLite index may be generated strictly as a derived cache for multi-hop recursive queries (e.g. transitive impact reachability). Canonical JSON remains the sole source of truth; the SQLite index can be purged or rebuilt at any time (and the owner reserves veto rights if JSON-only performance is sufficient).

## Alternatives considered
- **YAML:** Rejected due to high parsing overhead, ambiguous typing (e.g. `yes`/`no` booleans), and larger file footprint.
- **Monolithic single `graph.json`:** Rejected because reading or modifying one node requires reading/writing the entire multi-megabyte file.
- **SQLite as Sole Store:** Rejected as primary because binary databases prevent granular git diffs and human inspection.

## Consequences
- Clean git diffs when only specific files are modified.
- Enables streaming low-context node cards without loading the entire graph into RAM.

## Notes
[[feat-graph-persistence]], [[moc-decisions]]
