---
id: feat-file-classification
type: feature
title: File Classification
summary: Classify each discovered file as Python, SQL, Shell, JSON, or YAML; mark unsupported or binary files gracefully.
status: active
tags: [phase2, discovery, classification]
code_refs: [repopeek/discovery/classifier.py]
depends_on: ['[[comp-discovery]]', '[[con-scope-languages]]', '[[feat-file-discovery]]']
affects: ['[[feat-json-parser]]', '[[feat-python-parser]]', '[[feat-sql-parser]]']
last_verified: 2026-10-03
source: "_sources/task_list.md §Phase 2 Step 5; RepoPeek Owner Briefing §4"
---

# File Classification

## Purpose
Routes each file to the appropriate parser engine. Unsupported files are cataloged with `parse_status: "unsupported"` rather than dropped silently, ensuring complete codebase inventory without traversal errors.

## Behavior / Contract
- Input: stream of file paths from [[feat-file-discovery]]
- Classification rules:
  - `.py`, `.pyi` → `FileType.PYTHON`
  - `.sql` → `FileType.SQL`
  - `.sh`, `.bash`, or shell shebang → `FileType.SHELL`
  - `.json` → `FileType.JSON`
  - `.yaml`, `.yml` → `FileType.YAML`
  - binary files → `parse_status: "skipped_binary"`
  - oversized files → `parse_status: "skipped_size"`
  - all other files → `FileType.OTHER`
- Output: typed stream of `DiscoveredFile` records

## Impact (blast radius)
- **Depends on:** [[feat-file-discovery]], [[comp-discovery]], [[con-scope-languages]]
- **Affects (downstream):** [[feat-python-parser]], [[feat-sql-parser]], [[feat-json-parser]]
- **If this changes, also review:** [[con-scope-languages]]

## Decisions & Constraints
[[con-scope-languages]], [[con-determinism]]

## Related
[[moc-features]]
