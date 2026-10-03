---
id: con-local-execution
type: constraint
title: Local Execution Requirement
summary: All repository analysis, AST parsing, and graph construction must run locally
  without external cloud calls except configured LLM.
status: active
tags: [constraint, privacy, security, local]
affects: ['[[comp-discovery]]', '[[comp-graph]]', '[[comp-parsers]]', '[[req-local-repo-analysis]]']
last_verified: 2026-10-03
source: "_sources/cursorrules.md \xA7Agent Operating Rules"
depends_on: []
---
# Local Execution Requirement

## Rule
All repository analysis, AST parsing, SQL dialect translation, graph persistence, and query traversals must run completely locally on the user's machine without external network calls. The only permitted external network connection is to the user-configured LLM API endpoint for semantic enrichment.

## Rationale
Protects proprietary enterprise source code from leaking over networks and ensures that core code discovery and AST parsing can function entirely offline and in air-gapped environments.

## What it prohibits
- Uploading raw source code files to remote analysis services.
- Sending telemetry or tracking packets to external servers.
- Requiring cloud credentials to perform deterministic parsing.

## Enforcement
- Code inspection and automated tests running in isolated network environments.

## Related
[[req-local-repo-analysis]], [[adr-003-no-distributed-infra]]
