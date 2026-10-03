---
id: 00-index
type: index
title: Repopeek Knowledge Vault — Root Index
summary: Root entry point for Repopeek intelligence graph documentation. Navigate via MOCs.
last_verified: 2026-10-03
---

# Repopeek Knowledge Vault — Root Index

> **Agent navigation rule:** Never read the entire vault or monolithic source documents. Start here, navigate to the relevant MOC below, and load only the 1–3 specific atomic notes required for your current task (≤ 2 hops).

---

## Maps of Content (MOCs)

| Map of Content | Focus & Scope |
|----------------|---------------|
| [[moc-architecture]] | Overall pipeline flow, component boundaries, and module architecture |
| [[moc-features]] | End-user and agent-facing capabilities (discovery, parsers, graph, enrichment, CLI) |
| [[moc-data-models]] | Schema definitions, node types (Repository, File, Function, SQL, JSON, Semantic), and edge taxonomy |
| [[moc-decisions]] | Architectural Decision Records (ADRs) and technical rationales |
| [[moc-open-questions]] | Unresolved questions, pending decisions, and architectural TBDs |

---

## Quick Reference & Entry Points

- **Vault Rules & Workflow:** [[conventions]]
- **Recent Updates:** [[changelog]]
- **Phase 2 Implementation Plan:** [[plan-phase-2]] (and [[log-phase-2]])
- **Target Repository Analysis Requirements:** [[req-local-repo-analysis]]
- **Deterministic Code Extraction Core:** [[req-deterministic-extraction]]
- **Semantic LLM Grounding & Provenance:** [[req-semantic-enrichment]], [[req-provenance]]
- **MVP Success Criteria:** [[req-mvp-success-criteria]]

---

## Active Architectural Constraints
- [[con-no-distributed-graph]] — No Neo4j/Memgraph or external graph databases
- [[con-no-cloud-saas]] — Prohibit cloud SaaS multi-tenancy
- [[con-determinism]] — Identical inputs yield identical deterministic graphs
- [[con-no-hallucination]] — Undocumented behaviors marked TBD
- [[con-scope-languages]] — Strictly Python, SQL (Oracle), and JSON
- [[con-local-execution]] — Offline execution except configured LLM endpoint
