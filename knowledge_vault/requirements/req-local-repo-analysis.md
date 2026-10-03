---
id: req-local-repo-analysis
type: requirement
title: Local Repository Analysis
summary: The system must accept a local filesystem directory as input and analyze
  its files without any remote calls.
status: implemented
tags: [mvp, scope]
code_refs: [repopeek/config.py, repopeek/cli.py]
depends_on: ['[[con-local-execution]]']
affects: ['[[comp-config]]', '[[comp-discovery]]', '[[feat-file-discovery]]', '[[req-mvp-success-criteria]]']
last_verified: 2026-10-03
source: "_sources/mvp_requirements.md \xA7In Scope"
---
# Local Repository Analysis

## Purpose
The MVP operates entirely locally. It takes a repository path as input and produces a graph from that directory. No git remote, no cloud service, and no network calls are involved in analysis.

## Behavior / Contract
- Input: a local filesystem path (absolute or relative) pointing to a repository root.
- All file traversal, parsing, and graph construction happen on that local directory.
- The configured LLM call is the only permitted external network call, and only during semantic enrichment.

## Impact (blast radius)
- **Depends on:** nothing upstream
- **Affects (downstream):** [[comp-discovery]], [[comp-config]], [[feat-file-discovery]]
- **If this changes, also review:** [[con-local-execution]], [[con-no-cloud-saas]]

## Decisions & Constraints
[[con-local-execution]], [[con-no-cloud-saas]]

## Related
[[moc-features]]
