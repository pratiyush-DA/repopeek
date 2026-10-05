---
id: feat-traversal-confidence
type: feature
title: Mathematical Traversal Confidence & Evidence-Backed Blast Radius
summary: Exponential multi-hop confidence decay, multi-path reinforcement, distance decay, and direct/indirect/excluded blast radius partitioning with exact file:line citations.
status: active
tags: [phase3, blast-radius, confidence, graph-traversal, evidence]
code_refs: [repopeek/graph/blast_radius.py, repopeek/graph/__init__.py, repopeek/query/engine.py, tests/test_blast_radius.py, tests/test_retrieval_reliability.py]
depends_on: ['[[plan-phase-3]]', '[[comp-graph]]', '[[comp-query]]', '[[feat-query-cli]]', '[[moc-features]]']
affects: ['[[log-phase-3]]', '[[feat-agent-mcp]]']
last_verified: 2026-10-05
---
# Mathematical Traversal Confidence & Evidence-Backed Blast Radius

## Purpose
Replaces heuristic, uncalibrated blast radius calculations with rigorous mathematical traversal confidence scoring and deterministic evidence citations, allowing coding agents to precisely assess the risk of changing any code symbol or schema entity.

## Mathematical Formulation
1. **Edge Prior Confidence ($c_{edge}$):**
   - Direct AST calls / inheritance: $0.95$
   - Data flow definitions & writes/reads: $0.85$
   - Module imports & script targets: $0.80$
   - Dynamic dispatch & ambiguous references: $0.50$
   - Unresolved / external heuristics: $0.30$
2. **Single-Path Confidence with Hop Decay:**
   $$PathConfidence(P) = \min\left(0.99, \left(\prod_{i=1}^{h} c_i\right) \cdot \exp(-0.25(h-1))\right)$$
   Penalizes long speculative chains exponentially while preserving high confidence for direct 1-hop dependencies.
3. **Multi-Path Reinforcement:**
   $$CombinedConfidence(N) = \min\left(0.99, 1 - \prod_{j=1}^{m} (1 - PathConfidence(P_j))\right)$$
   Multiple distinct call/read paths to the same destination reinforce the impact likelihood monotonically.
4. **Distance Decay (Graph Relevance Score):**
   $$GraphScore(N) = CombinedConfidence(N) \cdot \exp(-0.70(d - 1))$$
   Decays contextual importance by hop distance $d \ge 1$.

## Blast Radius Partitioning
- **`direct`**: $d = 1$ dependencies with $CombinedConfidence \ge 0.50$ (or $CombinedConfidence \ge 0.80$).
- **`indirect`**: $d > 1$ dependencies with $CombinedConfidence \ge 0.20$.
- **`excluded`**: Nodes whose confidence decays below $0.20$ or exceeds depth limits, annotated with explicit `exclusion_reason`.

## Hard Negative Exclusion Pruning (`is_node_excluded`)
- Prevents blast-radius traversal contamination across explicitly excluded directories (e.g. `shipping/`), files (`shipping.py`), symbols (`ShippingService`), and glob patterns (`**/shipping/**`).
- Nodes matching an exclusion rule are hard-pruned *before* queue expansion or path recording, guaranteeing zero false inclusions in compiled context packages (`NEGATIVE_RETRIEVAL_FAILURE = 0`).

## Evidence Citations
Every affected node records exact source locations (`file:start-end` or `file:line`) and full hop chains (`src`, `dst`, `type`, `confidence`, `flow`, `citation`).

## Interfaces
- **Python:** `GraphQueryEngine.blast_radius(...) -> BlastRadiusReport`
- **Enriched Impact:** `GraphQueryEngine.impact(...) -> Dict[str, Any]` (backward-compatible)
