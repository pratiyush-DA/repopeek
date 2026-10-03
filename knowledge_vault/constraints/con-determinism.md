---
id: con-determinism
type: constraint
title: Deterministic Layer Reproducibility
summary: Identical codebase inputs must always yield identical deterministic graph
  nodes and edges across runs.
status: active
tags: [constraint, determinism, quality]
affects: ['[[comp-discovery]]', '[[comp-graph]]', '[[comp-parsers]]', '[[req-deterministic-extraction]]']
last_verified: 2026-10-03
source: "_sources/cursorrules.md \xA7Agent Operating Rules"
depends_on: []
---
# Deterministic Layer Reproducibility

## Rule
The deterministic layer (file discovery, file classification, Python parsing, SQL parsing, JSON parsing, and baseline graph construction) must be 100% deterministic and reproducible. Given the same repository commit, running the pipeline multiple times must yield byte-for-byte or semantically identical nodes and edges.

## Rationale
Downstream AI agents and developers rely on deterministic nodes as the bedrock of ground truth. If base node IDs or edge relationships fluctuate randomly between runs, provenance breaks and differential analysis becomes impossible.

## What it prohibits
- Sorting files or nodes non-deterministically (e.g. un-ordered `os.listdir()` or set iteration without sorting).
- Using random UUIDs for deterministic node IDs (IDs must be hash- or path-derived).
- Introducing LLM inferences or non-deterministic heuristics into the parsing phase.

## Enforcement
- Automated tests verifying that running the parser twice on identical inputs generates identical graph node and edge sets.

## Related
[[req-deterministic-extraction]], [[feat-graph-construction]]
