---
id: feat-provenance-binding
type: feature
title: Provenance Binding
summary: Attach verifiable code origin metadata, line numbers, deterministic node
  references, and confidence scores to all LLM-generated semantic nodes.
status: planned
tags: [phase5, provenance, verification]
code_refs: [repopeek/enrichment/]
depends_on: ['[[comp-enrichment]]', '[[con-no-hallucination]]', '[[data-edge-types]]',
  '[[data-node-businessprocess]]', '[[data-node-function]]', '[[data-node-story]]',
  '[[feat-semantic-enrichment]]', '[[req-provenance]]', '[[req-semantic-enrichment]]']
affects: ['[[data-edge-types]]', '[[data-node-businessprocess]]', '[[data-node-story]]']
last_verified: 2026-10-03
source: "_sources/mvp_requirements.md \xA7Provenance"
---
# Provenance Binding

## Purpose
Guarantees trust and auditability for all LLM-derived knowledge. Every semantic synthesis must cite its exact deterministic code foundation, allowing agents and developers to trace any high-level statement back to physical source lines.

## Behavior / Contract
- Input: Semantic nodes generated during [[feat-semantic-enrichment]]
- Output: Enriched semantic nodes and edges fulfilling:
  - `IMPLEMENTS` edges pointing directly to [[data-node-function]] and [[data-node-file]] IDs
  - Attribute `confidence`: float value between 0.0 and 1.0 reflecting certainty
  - Explicit file paths and line ranges bound to the documentation claim
  - (Optional/TBD) `provenance_commit`: Git commit SHA anchoring the analysis snapshot
- Invariant: A semantic node with no deterministic anchors is discarded as an ungrounded hallucination.

## Impact (blast radius)
- **Depends on:** [[feat-semantic-enrichment]], [[req-provenance]]
- **Affects (downstream):** [[data-node-businessprocess]], [[data-node-story]], [[data-edge-types]]
- **If this changes, also review:** [[con-no-hallucination]], [[req-deterministic-extraction]]

## Related
[[moc-features]], [[moc-architecture]]
