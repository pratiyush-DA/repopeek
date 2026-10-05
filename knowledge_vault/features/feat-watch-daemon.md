---
id: feat-watch-daemon
type: feature
title: Incremental Watch Daemon
summary: Background file-watching daemon providing real-time incremental graph, shard, and SQLite index synchronization in <50ms without external dependencies.
status: verified
tags: [watch, daemon, incremental, sync, graph]
code_refs: [repopeek/daemon/watcher.py, repopeek/daemon/__init__.py, repopeek/cli.py]
depends_on: ['[[feat-graph-persistence]]', '[[feat-graph-construction]]', '[[plan-phase-3]]']
affects: ['[[log-phase-3]]']
last_verified: 2026-10-05
---

# Incremental Watch Daemon

## 1. Executive Summary & Purpose
During active software development, full repository re-indexing after every save creates intolerable latency. The `RepoPeekWatcher` daemon runs as a lightweight, zero-dependency background process that observes repository modifications and updates the in-memory property graph, storage shards, and SQLite search cache in under 50ms per modified file.

## 2. Architecture & Design Principles
1. **Ponytail Full Mode (Stdlib First):** Built entirely with Python standard library filesystem APIs (`st_mtime_ns` and `st_size` tracking) to ensure cross-platform execution on Windows, Ubuntu, and macOS without requiring native binaries or heavy external watchdog wheels.
2. **Debouncing & Batching:** Features configurable debounce intervals to collapse multiple rapid editor writes or auto-format operations into single atomic sync passes.
3. **Targeted Incremental Updates:** Only the modified file is re-parsed; obsolete nodes and invalid edges are purged from the graph and regenerated in-place.
4. **Synchronized Persistence:** Immediately writes the updated file shard (`update_file_shard`), syncs `manifest.json`, and updates the SQLite traversal and FTS5 search index (`update_sqlite_file`).
5. **Deletion Resilience:** Removing a file from the repository automatically purges its orphaned nodes and invalid dangling edges from the property graph.

## 3. CLI Operation
- Run daemon: `repopeek --watch`
- Custom poll interval: `repopeek --watch --watch-interval 0.5`
- Graceful shutdown on `Ctrl+C` with clean shutdown logging.
