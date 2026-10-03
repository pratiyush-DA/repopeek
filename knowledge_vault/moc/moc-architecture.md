---
id: moc-architecture
type: moc
title: "Architecture \u2014 Map of Content"
summary: Hub for all architectural components, multi-agent pipeline stages, and data
  flows in Repopeek.
last_verified: 2026-10-03
affects: ['[[plan]]']
depends_on: []
---
# Architecture — Map of Content

> Hub note for Repopeek multi-agent architecture and pipeline flow.

## High-Level Architecture Pipeline

```mermaid
graph TD
    Repo[Local Repository] --> Scanner[1. Scanner Agent]
    Scanner --> Parsers[2. Language Parsers: Tree-Sitter / AST / SQLGlot]
    Parsers --> Resolver[3. Cross-File Symbol Resolver]
    Resolver --> Builder[4. Graph Builder]
    Builder --> Canonical[(Canonical Property Graph)]
    Canonical --> Analyzer[5. Graph Analyzer: Impact / Hotspots]
    Canonical --> Storyteller[6. Storyteller: 5-Tier Cascade]
    Storyteller --> Verifier[7. Fact Verifier & Schema Validator]
    Verifier --> Packager[8. Packager: Sharded JSON & Lenses]
    Packager --> Lenses[(Materialised Lens Graphs)]
    Lenses --> Retrieval[9. Low-Context Query & Context-Pack Service]
    Retrieval --> CLI[CLI Interface: repopeek]
    Retrieval --> MCP[MCP Server: repopeek serve-mcp]
```

## Core Agent & Component Pipeline Stages

1. **Scanner Stage:** [[comp-discovery]] — crawls repository, respects `.repopeekignore`, computes content & git blob SHAs.
2. **Deterministic Parsers:** [[comp-parsers]] — Python (AST + tree-sitter), SQL (SQLGlot Oracle/Postgres), Shell (tree-sitter-bash), JSON, YAML.
3. **Symbol Resolver:** Connects cross-file imports, method calls, and cross-language bridges (Python -> SQL tables, Shell -> Python scripts).
4. **Graph Builder:** [[comp-graph]] — builds in-memory NetworkX directed multigraph with stable URIs.
5. **Enrichment & Storyteller:** [[comp-enrichment]] — 5-tier cascade under cost governor, generating node card stories (see [[run-swap-llm-provider]] for provider guide).
6. **Query & Context-Pack Service:** [[comp-query]] — `lookup`, `neighbors`, `impact`, `data_trace`, and `context_pack`.
7. **Infrastructure & Interfaces:** [[comp-config]], [[comp-cli]], and [[adr-011-mcp-interface]].

## Cross-Cutting Architecture Decisions
- In-memory Property Graph: [[adr-001-networkx-local-graph]]
- Sharded JSON Persistence: [[adr-004-graph-persistence-tbd]]
- Hybrid Parser Stack: [[adr-005-python-parser-tbd]]
- Pluggable LLM Provider & Groq: [[adr-006-llm-provider-abstraction]]
- Story Cost Cascade: [[adr-007-story-cost-cascade]]
- Canonical Graph & 11 Lenses: [[adr-008-canonical-graph-lenses]]
- Git Provenance & Incremental Updates: [[adr-009-provenance-incremental-updates]]
- Asyncio Orchestration: [[adr-010-multi-agent-orchestration]]
- MCP Interface: [[adr-011-mcp-interface]]
- Secret Redaction & Privacy: [[adr-012-secrets-and-privacy]]

## Maps of Content
- Decisions: [[moc-decisions]]
- Data Models & Lenses: [[moc-data-models]]
- Features: [[moc-features]]
- Implementation Plan: [[plan-phase-2]]
