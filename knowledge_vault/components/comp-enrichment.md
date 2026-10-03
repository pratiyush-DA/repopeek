---
id: comp-enrichment
type: component
title: Enrichment Component
summary: Module repopeek/enrichment/ executing LLM-based semantic enrichment and provenance
  binding.
status: planned
tags: [phase5, component, enrichment, llm]
code_refs: [repopeek/enrichment/]
depends_on: ['[[comp-config]]', '[[comp-graph]]', '[[con-no-hallucination]]', '[[data-node-businessprocess]]',
  '[[data-node-story]]', '[[feat-semantic-enrichment]]']
affects: ['[[comp-query]]', '[[feat-provenance-binding]]', '[[feat-semantic-enrichment]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 5"
---
# Enrichment Component

## Purpose
Orchestrates LLM prompts and responses to add semantic layers atop deterministic code facts. Synthesizes business process flows and user stories, while binding verifiable line-level provenance and confidence scores.

## Responsibilities
- Format graph subgraphs into prompt contexts for LLM completion.
- Execute structured prompts for function summaries, module descriptions, and business processes.
- Bind generated semantic nodes (`BusinessProcess`, `Story`) to deterministic code nodes (`Function`, `File`) via `IMPLEMENTS` edges.
- Compute confidence metrics and enforce anti-hallucination rules (tagging unknowns as TBD).

## Interface / Contract
- `EnrichmentPipeline.enrich(graph: NetworkXGraph) -> NetworkXGraph`
- `ProvenanceBinder.bind(semantic_node: Node, code_nodes: List[Node]) -> Edge`
- Inputs: Validated deterministic NetworkX graph
- Outputs: Enriched NetworkX graph with semantic nodes and provenance attributes
- Errors: Handles API timeouts and parsing failures with fallbacks.

## Impact (blast radius)
- **Depends on:** [[comp-graph]], [[comp-config]]
- **Affects (downstream):** [[comp-query]], [[feat-semantic-enrichment]], [[feat-provenance-binding]]
- **If this changes, also review:** [[req-provenance]], [[con-no-hallucination]]
- **Data touched:** [[data-node-businessprocess]], [[data-node-story]], [[data-edge-types]]

## Decisions & Constraints
[[con-no-hallucination]], [[req-provenance]], [[req-semantic-enrichment]]

## Related
[[moc-architecture]]
