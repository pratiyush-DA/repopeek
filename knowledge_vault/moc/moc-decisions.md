---
id: moc-decisions
type: moc
title: "Decisions \u2014 Map of Content"
summary: Hub for all Architecture Decision Records (ADRs) in Repopeek.
last_verified: 2026-10-03
affects: ['[[plan]]']
depends_on: ['[[adr-004-graph-persistence-tbd]]', '[[adr-005-python-parser-tbd]]',
  '[[adr-006-llm-provider-abstraction]]', '[[adr-007-story-cost-cascade]]', '[[adr-008-canonical-graph-lenses]]',
  '[[adr-009-provenance-incremental-updates]]', '[[adr-010-multi-agent-orchestration]]',
  '[[adr-011-mcp-interface]]', '[[adr-012-secrets-and-privacy]]']
---
# Decisions — Map of Content

> Hub note only. No content of its own.

## Accepted Decisions
- [[adr-001-networkx-local-graph]] — NetworkX as in-memory property graph engine
- [[adr-002-sqlglot-oracle-dialect]] — SQLGlot with Oracle dialect for deterministic SQL parsing
- [[adr-003-no-distributed-infra]] — Prohibition of distributed databases/SaaS for MVP
- [[adr-004-graph-persistence-tbd]] — Canonical sharded JSON with optional SQLite traversal cache
- [[adr-005-python-parser-tbd]] — Hybrid parsing stack: tree-sitter + stdlib AST + SQLGlot
- [[adr-006-llm-provider-abstraction]] — Pluggable LLMProvider abstraction & abstract model tiers (Groq primary)
- [[adr-007-story-cost-cascade]] — Five-tier cost cascade (deterministic first, content-cache, cheap model, verifier)
- [[adr-008-canonical-graph-lenses]] — Canonical property graph with materialised lens subgraphs
- [[adr-009-provenance-incremental-updates]] — Git commit/blob binding, git diff incremental indexer, atomic swaps
- [[adr-010-multi-agent-orchestration]] — Typed task graph workflow engine on asyncio
- [[adr-011-mcp-interface]] — MCP server for external agent queries (internal pipelines use direct Python)
- [[adr-012-secrets-and-privacy]] — Environment secrets, client-side PII/secret redaction, offline mode

## Related Constraints
- [[con-no-distributed-graph]]
- [[con-no-cloud-saas]]
- [[con-scope-languages]]
- [[con-determinism]]
- [[con-no-hallucination]]
- [[con-local-execution]]

## Open Questions & Backlog
- [[moc-open-questions]]
