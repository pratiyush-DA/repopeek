---
id: feat-file-discovery
type: feature
title: File Discovery
summary: Recursively traverse a local repository directory and yield all candidate
  files, respecting ignore rules for virtual envs, caches, and hidden dirs.
status: active
tags: [phase2, discovery]
code_refs: [repopeek/discovery/crawler.py, repopeek/discovery/ignore.py]
depends_on: ['[[comp-config]]', '[[comp-discovery]]', '[[req-local-repo-analysis]]']
affects: ['[[comp-discovery]]', '[[feat-file-classification]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 2 Step 4"
---
# File Discovery

## Purpose
Entry point for all analysis. Walks the target repository and produces the ordered list of files that will be classified and then parsed. Must be deterministic and efficient.

## Behavior / Contract
- Input: `repo_path` from [[comp-config]]
- Output: iterator of absolute file paths
- Skip: `.git/`, `.venv/`, `__pycache__/`, `node_modules/`, and any configured ignore patterns
- Max file size threshold: configurable via `max_file_size_kb` (default 2048 KB)
- Deterministic: directory walk order must be sorted to ensure reproducible output

## Impact (blast radius)
- **Depends on:** [[req-local-repo-analysis]], [[comp-config]]
- **Affects (downstream):** [[feat-file-classification]] (receives the file list)
- **If this changes, also review:** [[comp-discovery]], [[con-determinism]]

## Decisions & Constraints
[[con-determinism]], [[con-local-execution]]

## Related
[[moc-features]]
