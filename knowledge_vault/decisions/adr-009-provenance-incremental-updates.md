---
id: adr-009-provenance-incremental-updates
type: decision
title: Git-Anchored Provenance and Differential Incremental Updates
summary: Bind every graph artifact to git commit and blob SHAs, enabling git-diff
  incremental re-indexing and atomic directory swaps.
status: accepted
tags: [architecture, git, provenance, incremental, adr]
code_refs: [repopeek/discovery/, repopeek/graph/]
depends_on: []
affects: ['[[comp-discovery]]', '[[comp-graph]]', '[[feat-provenance-binding]]', '[[moc-decisions]]']
last_verified: 2026-10-03
source: "RepoPeek Owner Briefing \xA72 & \xA78"
---
# ADR-009: Git-Anchored Provenance and Differential Incremental Updates

## Status
Accepted

## Context
Re-indexing an entire repository on every minor code edit is slow and wasteful. Furthermore, consumers of the graph need guarantees that node cards reflect the exact commit they are modifying, with staleness warnings if local edits have drifted.

## Decision
1. **Provenance Metadata:** Every graph artifact records:
   - `repo_commit`: Git commit SHA (`git rev-parse HEAD`).
   - `dirty`: Boolean indicating whether unstaged/uncommitted changes were present.
   - `file_blob_sha`: Git blob SHA per file.
   - `tool_version` & `schema_version`.
   - Fallback: Non-git directories use content SHA-256 hashes with `commit: null`.
2. **Incremental Indexing:**
   - Detect changed files using `git diff --name-status <old_sha>..<new_sha>`.
   - Re-parse only modified or added files; delete removed nodes and incoming/outgoing edges.
   - Invalidate dependent story cache keys.
3. **Atomic Writes:** Graph indexing writes to a temporary directory (`.repopeek/tmp_build/`) and performs an atomic directory swap on completion, guaranteeing that partial or failed runs never corrupt active graph state.

## Consequences
- Fast sub-second re-indexing for PR changes.
- Safe concurrent reading during indexing runs.

## Notes
[[feat-provenance-binding]], [[moc-decisions]]
