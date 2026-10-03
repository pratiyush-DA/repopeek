---
id: comp-discovery
type: component
title: Discovery Component
summary: Module repopeek/discovery/ responsible for file tree traversal, ignore filtering,
  and file type classification.
status: planned
tags: [phase2, component, discovery]
code_refs: [repopeek/discovery/]
depends_on: ['[[comp-config]]', '[[con-determinism]]', '[[con-local-execution]]',
  '[[con-scope-languages]]', '[[feat-file-discovery]]', '[[req-local-repo-analysis]]']
affects: ['[[comp-parsers]]', '[[feat-file-classification]]', '[[feat-file-discovery]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 2"
---
# Discovery Component

## Purpose
Owns repository scanning and file categorization. Discovers files within the target repo directory, enforces ignore rules, and maps each relevant file to its parser classification (Python, SQL, JSON).

## Responsibilities
- Recursively crawl directory structures while ignoring VCS (`.git`), virtualenvs, caches, and user-specified ignore patterns.
- Filter out binary files and files exceeding maximum allowed size.
- Classify files into supported extensions (`.py`, `.sql`, `.json`) and discard unsupported files.

## Interface / Contract
- `discover_files(repo_path: Path, config: RepopeekConfig) -> Iterator[DiscoveredFile]`
- `classify_file(file_path: Path) -> FileType`
- Inputs: Target repository path, configuration options
- Outputs: Stream of categorized discovered file records
- Errors: Raises `InvalidRepositoryError` if path does not exist or is not a directory.

## Impact (blast radius)
- **Depends on:** [[comp-config]]
- **Affects (downstream):** [[comp-parsers]], [[feat-file-discovery]], [[feat-file-classification]]
- **If this changes, also review:** [[con-scope-languages]], [[con-determinism]]
- **Data touched:** [[data-node-repository]], [[data-node-file]]

## Decisions & Constraints
[[con-scope-languages]], [[con-determinism]], [[con-local-execution]]

## Related
[[moc-architecture]]
