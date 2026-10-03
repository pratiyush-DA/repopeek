---
id: adr-010-multi-agent-orchestration
type: decision
title: Lightweight Typed Task Graph Orchestration on Asyncio
summary: Implement multi-agent workflows using a typed task graph on native Python
  asyncio without external heavy agent frameworks.
status: accepted
tags: [architecture, multi-agent, asyncio, workflow, adr]
code_refs: []
depends_on: []
affects: ['[[comp-cli]]', '[[comp-graph]]', '[[moc-decisions]]']
last_verified: 2026-10-03
source: "RepoPeek Owner Briefing \xA72 & \xA79"
---
# ADR-010: Lightweight Typed Task Graph Orchestration on Asyncio

## Status
Accepted

## Context
RepoPeek's pipeline consists of several distinct stages: Scanner, Language Parsers, Resolver, Graph Builder, Analyzer, Storyteller, Verifier, and Packager. Heavy frameworks (e.g. LangGraph, CrewAI, AutoGen) introduce massive dependency bloat, opaque state machines, and non-deterministic overhead for pipelines that are largely deterministic.

## Decision
1. **Engine:** Use a lightweight, typed task graph implemented on native Python `asyncio` and Pydantic message schemas.
2. **Pipeline Stages:**
   - **Scanner:** Traversal, ignore rules, content hashing.
   - **Parser Agents:** Parallel deterministic AST and CST extraction.
   - **Resolver:** Cross-file import and name resolution.
   - **Graph Builder:** In-memory multigraph construction and lens derivation.
   - **Analyzer:** Reachability, impact radius, hotspot metrics.
   - **Storyteller:** Five-tier LLM story generation under a cost governor.
   - **Verifier:** Graph invariant and anti-hallucination fact verification.
   - **Packager:** Sharded JSON persistence and Markdown/Mermaid generation.
3. **Execution Modes:** Clear CLI subcommands (`repopeek index`, `repopeek update`, `repopeek query`, `repopeek stories --dry-run`).

## Alternatives considered
- **LangGraph / CrewAI:** Rejected due to excessive abstractions and unwanted dependencies for deterministic static analysis.

## Consequences
- Fast startup (<100ms CLI latency), zero framework lock-in, fully debuggable async execution.

## Notes
[[moc-architecture]], [[moc-decisions]]
