---
id: feat-context-compiler
type: feature
title: Context Compiler, Constraint Extractor & Change Plan Generator
summary: Task-driven context compiler packaging entrypoints, calibrated blast radius, multi-tier constraints, and risk-assessed change plans with progressive disclosure.
status: active
tags: [phase3, context-compiler, constraints, change-plan]
code_refs: [repopeek/context/__init__.py, repopeek/context/compiler.py, repopeek/query/engine.py, repopeek/cli.py, tests/test_context_compiler.py]
depends_on: ['[[plan-phase-3]]', '[[feat-intent-retrieval]]', '[[feat-traversal-confidence]]', '[[comp-query]]', '[[moc-features]]']
affects: ['[[log-phase-3]]']
last_verified: 2026-10-05
---
# Context Compiler, Constraint Extractor & Change Plan Generator

## Purpose
Translates high-level natural language engineering tasks directly into minimal, evidence-backed `ContextPackage` artifacts, eliminating token bloat and blind file explorations by coding agents.

## Core Capabilities
1. **Context Compilation (`ContextCompiler.compile`):**
   - Synthesizes intent-to-symbol resolution (top candidates) with mathematical blast radius (direct, indirect, excluded).
   - Injects relevant source code snippets for zero-read code modifications.
   - Computes token economics: estimated tokens, raw file equivalent, and percentage reduction (typically 80–95%).
2. **Progressive Disclosure Markdown Rendering (`ContextPackage.to_markdown`):**
   - **Level 1 (Brief, ~250–400 tokens):** Executive task summary, candidate entrypoints, direct blast radius, and high-level change plan.
   - **Level 2 (Standard, ~600–1000 tokens):** Adds signatures, indirect blast radius, excluded node rationale, and structural constraints.
   - **Level 3 (Full, ~1200–1800 tokens):** Embeds exact source code snippets for candidate entrypoints and direct targets.
3. **Multi-Tier Constraint Extraction (`_extract_constraints`):**
   - Parameter and type constraints (`params`).
   - Return type invariants (`returns`).
   - Exception boundaries (`raises`).
   - Database schema table dependencies.
   - Behavioral invariants derived from semantic stories.
4. **Engineering Change Plan Generator (`_generate_plan`):**
   - Determines risk level (`LOW`, `MEDIUM`, `HIGH`) from downstream blast radius and schema coupling.
   - Outputs ordered phases: Pre-Change Verification, Core Modifications, Blast Radius Adjustments, and Post-Change Regression Validation.

## Interfaces
- **Python API:** `GraphQueryEngine.compile_context(task, budget=1500, level=2) -> ContextPackage`
- **CLI Commands:**
  - `repopeek --context "<task>" [--budget 1500] [--level 1|2|3] [--snippet]`
  - `repopeek --plan "<task>"`
