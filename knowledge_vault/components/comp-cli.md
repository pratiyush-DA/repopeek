---
id: comp-cli
type: component
title: CLI Component
summary: Module repopeek/cli.py providing command-line argument parsing and the main
  entry point executable.
status: active
tags: [phase1, component, cli]
code_refs: [repopeek/cli.py]
depends_on: ['[[adr-010-multi-agent-orchestration]]', '[[comp-config]]', '[[comp-query]]',
  '[[con-no-cloud-saas]]', '[[feat-query-cli]]']
affects: ['[[comp-query]]', '[[feat-query-cli]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 1"
---
# CLI Component

## Purpose
The primary binary entry point for the Repopeek suite. Parses CLI flags, applies configuration overrides, performs pre-flight checks, and will orchestrate pipeline phases.

## Responsibilities
- Construct argument parser (`argparse`) with flags (`--repo-path`, `--output-dir`, `--config`, `--sql-dialect`, `--check`, `--version`).
- Merge command-line options with `RepopeekConfig`.
- Validate repository existence and execute health checks.
- Expose executable command `repopeek` registered in `pyproject.toml`.

## Interface / Contract
- `build_parser() -> argparse.ArgumentParser`
- `main(argv: Optional[List[str]] = None) -> int`
- Entry point: `repopeek = "repopeek.cli:main"`

## Impact (blast radius)
- **Depends on:** [[comp-config]]
- **Affects (downstream):** [[comp-query]], [[feat-query-cli]]
- **If this changes, also review:** [[feat-query-cli]]
- **Data touched:** none

## Decisions & Constraints
[[con-local-execution]]

## Related
[[moc-architecture]]
