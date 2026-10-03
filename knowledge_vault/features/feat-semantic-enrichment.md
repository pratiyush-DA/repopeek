---
id: feat-semantic-enrichment
type: feature
title: Semantic Enrichment
summary: Utilize an LLM pipeline to synthesize business processes, user stories, and
  high-level architecture over deterministic graph nodes.
status: planned
tags: [phase5, enrichment, llm]
code_refs: [repopeek/enrichment/]
depends_on: ['[[adr-007-story-cost-cascade]]', '[[comp-enrichment]]', '[[con-no-hallucination]]',
  '[[data-node-businessprocess]]', '[[data-node-story]]', '[[feat-graph-construction]]',
  '[[feat-graph-validation]]', '[[req-semantic-enrichment]]']
affects: ['[[comp-enrichment]]', '[[data-node-businessprocess]]', '[[data-node-story]]',
  '[[feat-provenance-binding]]']
last_verified: 2026-10-03
source: "_sources/architecture_documentation.md \xA7Semantic Enrichment"
---
# Semantic Enrichment

## Purpose
Bridges raw AST code facts with human and agent conceptual understanding. An LLM ingests deterministic graph subgraphs and generates high-level business capabilities, workflows, and stories grounded in verified source nodes.

## Behavior / Contract
- Input: Validated property graph containing deterministic code nodes
- Pipeline Phases:
  1. Function Summaries: Summarize function purpose from AST, docstrings, and call signatures
  2. Module Summaries: Aggregate function summaries and file structure to understand module responsibilities
  3. BusinessProcess Discovery: Identify coherent end-to-end execution paths and create [[data-node-businessprocess]] nodes
  4. Story Formulation: Generate actionable [[data-node-story]] nodes representing user-facing capabilities
- Grounding: Semantic nodes must never be free-floating; they must link via `IMPLEMENTS` edges to the concrete functions and files implementing them.
- Handling Uncertainty: Ambiguous or undocumented logic must be marked TBD per [[con-no-hallucination]].

## Impact (blast radius)
- **Depends on:** [[feat-graph-construction]], [[feat-graph-validation]], [[req-semantic-enrichment]]
- **Affects (downstream):** [[feat-provenance-binding]], [[data-node-businessprocess]], [[data-node-story]], [[comp-enrichment]]
- **If this changes, also review:** [[req-provenance]], [[con-no-hallucination]]

## Related
[[moc-features]], [[moc-architecture]]
