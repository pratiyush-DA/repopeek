---
id: feat-file-classification
type: feature
title: File Classification
summary: Classify each discovered file as Python, SQL, or JSON based on extension;
  silently skip unsupported types.
status: planned
tags: [phase2, discovery]
code_refs: [repopeek/discovery/]
depends_on: ['[[comp-discovery]]', '[[con-scope-languages]]', '[[feat-file-discovery]]']
affects: ['[[feat-json-parser]]', '[[feat-python-parser]]', '[[feat-sql-parser]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 2 Step 5"
---
# File Classification

## Purpose
Routes each file to the correct parser. Unsupported extensions are silently dropped; no error should be raised for unknown file types in the MVP.

## Behavior / Contract
- Input: stream of file paths from [[feat-file-discovery]]
- Classification rules (from [[comp-config]] `supported_extensions`):
  - `.py` → Python parser
  - `.sql` → SQL parser
  - `.json` → JSON parser
  - anything else → skip
- Output: typed stream of `(FileType, path)` pairs

## Impact (blast radius)
- **Depends on:** [[feat-file-discovery]], [[comp-config]]
- **Affects (downstream):** [[feat-python-parser]], [[feat-sql-parser]], [[feat-json-parser]]
- **If this changes, also review:** [[con-scope-languages]] (adding a language type here widens scope)

## Decisions & Constraints
[[con-scope-languages]]

## Related
[[moc-features]]
