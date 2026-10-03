---
id: comp-config
type: component
title: Config Component
summary: Module repopeek/config.py defining Pydantic model RepopeekConfig with validation
  and file serialization.
status: active
tags: [phase1, component, configuration]
code_refs: [repopeek/config.py]
depends_on: ['[[req-local-repo-analysis]]']
affects: ['[[comp-cli]]', '[[comp-discovery]]', '[[comp-enrichment]]', '[[comp-graph]]',
  '[[feat-file-discovery]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 1"
---
# Config Component

## Purpose
Provides centralized, validated configuration settings and sensible defaults for repository analysis, parser dialects, output paths, and operational limits.

## Responsibilities
- Define `RepopeekConfig` schema using Pydantic `BaseModel`.
- Manage parameters: `repo_path`, `supported_extensions`, `output_dir`, `graph_filename`, `sql_dialect`, `max_file_size_kb`, `log_level`.
- Provide serialization to/from JSON configuration files.
- Compute derived properties such as `graph_output_path`.

## Interface / Contract
- `RepopeekConfig(repo_path: Path, output_dir: Path, ...)`
- `RepopeekConfig.from_json_file(filepath: Path) -> RepopeekConfig`
- `RepopeekConfig.to_json_file(filepath: Path) -> None`
- Property: `graph_output_path -> Path`

## Impact (blast radius)
- **Depends on:** none (foundational)
- **Affects (downstream):** [[comp-cli]], [[comp-discovery]], [[comp-graph]], [[feat-file-discovery]]
- **If this changes, also review:** [[comp-cli]], [[con-determinism]]
- **Data touched:** none

## Decisions & Constraints
[[con-local-execution]], [[con-scope-languages]]

## Related
[[moc-architecture]]
