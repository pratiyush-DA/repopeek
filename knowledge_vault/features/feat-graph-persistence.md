---
id: feat-graph-persistence
type: feature
title: Graph Persistence
summary: Serialize and deserialize the in-memory property graph to and from local disk storage.
status: active
tags: [phase4, storage, persistence]
code_refs: [repopeek/storage/json_store.py, repopeek/storage/provenance.py, repopeek/storage/sqlite_cache.py, repopeek/storage/obsidian_exporter.py, repopeek/storage/__init__.py, repopeek/export/html.py]
depends_on: ['[[adr-004-graph-persistence-tbd]]', '[[comp-graph]]', '[[data-graph-lenses]]',
  '[[feat-graph-construction]]', '[[feat-graph-validation]]', '[[feat-wiki-export]]']
affects: ['[[comp-query]]', '[[feat-query-cli]]', '[[feat-watch-daemon]]']
last_verified: 2026-10-18
source: "_sources/task_list.md §Phase 4"
---
# Graph Persistence

## Purpose
Enables storing the constructed code intelligence graph locally so that subsequent queries, traversals, and enrichment runs do not require re-parsing the target codebase from scratch.

## Behavior / Contract
- **Input:** Canonical property graph (`CanonicalGraph`) with attached Git provenance and file blob SHAs.
- **Output:** Deterministic sharded JSON files (`graph.json`, `manifest.json`, `lenses/`, `shards/`) and derived SQLite cache (`cache.db`).
- **Deterministic JSON:** Keys sorted, indent=2, nulls excluded, SHA-256 integrity verification.
- **Materialized Lenses:** Subgraphs for `module`, `symbol`, `call`, `class`, `data`, `data_entity`, `config`, `process`, and `bridges`.
- **Atomic Writes:** Staged in temporary directories with atomic rename swap ensuring zero partial-write corruption.
- **Incremental Single-File Updates:** `GraphBuilder.update_file` incrementally parses a modified file, updates AST nodes and caller edges, and synchronizes the shard via `update_file_shard` and SQLite tables via `update_sqlite_file` in <50ms without full-repo rebuilds.
- **SQLite Cache:** Ephemeral SQLite schema (`nodes`, `edges`, `metadata`) with recursive CTE query engine (`query_sqlite_impact`) for sub-millisecond impact traversal.
- **Obsidian Vault Export:** `export_to_obsidian_vault` generates atomic markdown notes with YAML frontmatter, `[[wikilinks]]`, and native Obsidian `.obsidian/graph.json` color groupings. `find_default_obsidian_vault` auto-detects the system active vault from local config (`%APPDATA%/obsidian/obsidian.json`), and `open_in_obsidian` dispatches `obsidian://open?path=` to launch the desktop application. `read_obsidian_node` allows fast querying of documentation notes.
- **Obsidian-Style Interactive HTML Engine:** `export_html` generates a standalone, zero-dependency HTML file (`graph.html`) featuring a dual-layer architecture: HTML5 Canvas 2D with HiDPI backing store for >5,000 nodes and >15,000 edges at 60 FPS, D3.js v7 force simulation with community-tiered radial dispersion, relaxed physics parameters (-350 charge, 110 link distance, 0.004 center gravity, 12px collision padding), automatic screen-fit framing, optical screen-space font size clamping (`10px` to `13px` constant readability), 5-tier progressive semantic text LOD gating (zoomed-out k < 0.85 strictly hides resting text to eliminate white-cloud clutter; landmark classes/files appear at k >= 0.85; full labels reveal on deep zoom), two-tier Coral Red (`#e05561`) spotlighting with incident edge emphasis and background dimming, instant hover micro-cards with 2-hop blast radius, pinned selection inspector drawer, and glassmorphic physics controls drawer.

## Impact (blast radius)
- **Depends on:** [[feat-graph-construction]], [[comp-graph]]
- **Affects (downstream):** [[feat-query-cli]], [[comp-query]]
- **If this changes, also review:** [[adr-004-graph-persistence-tbd]], [[con-no-distributed-graph]], [[con-local-execution]]

## Related
[[moc-features]], [[moc-architecture]]
