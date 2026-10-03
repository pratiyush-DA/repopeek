---
id: moc-architecture
type: moc
title: "Architecture \u2014 Map of Content"
summary: Hub for all architectural components and pipeline flows in Repopeek.
last_verified: 2026-10-03
affects: []
depends_on: []
---
# Architecture — Map of Content

> Hub note only. No content of its own.

## Pipeline stages

- [[comp-discovery]] — file traversal and classification entry point
- [[comp-parsers]] — Python / SQL / JSON deterministic AST parsers
- [[comp-graph]] — in-memory graph construction, validation, persistence
- [[comp-enrichment]] — LLM semantic enrichment and provenance binding
- [[comp-query]] — graph inspection and impact traversal CLI

## Supporting components

- [[comp-config]] — runtime configuration model (`RepopeekConfig`)
- [[comp-cli]] — top-level argument parser and entry point

## Cross-cutting concerns

- [[con-determinism]] — identical input → identical output rule
- [[con-no-hallucination]] — no invented behavior
- [[con-local-execution]] — no external services except configured LLM

## Decisions

- [[moc-decisions]]

## See also

- [[moc-data-models]] — graph node and edge schemas
- [[moc-features]] — agent-facing capabilities
