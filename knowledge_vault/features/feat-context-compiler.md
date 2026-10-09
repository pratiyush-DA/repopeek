---
id: feat-context-compiler
type: feature
title: Context Compiler, Constraint Extractor & Change Plan Generator
summary: Task-driven context compiler with relative file-score trimming under a 4-file cap, token-budget enforcement, span snippets, and hard path/symbol exclusion stripping so packs stay small, in-budget, and leak-resistant.
status: active
tags: [phase3, context-compiler, constraints, change-plan]
code_refs: [repopeek/context/__init__.py, repopeek/context/compiler.py, repopeek/query/engine.py, repopeek/cli.py, tests/test_context_compiler.py]
depends_on: ['[[plan-phase-3]]', '[[feat-intent-retrieval]]', '[[feat-traversal-confidence]]', '[[comp-query]]', '[[moc-features]]']
affects: ['[[log-phase-3]]', '[[feat-agent-mcp]]', '[[feat-session-telemetry]]']
last_verified: 2026-10-09
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
   - Determines risk level (`LOW`, `MEDIUM`, `HIGH`) from the **full pre-trim** downstream blast radius and schema coupling, so file-count trimming never softens a HIGH/schema assessment (`risk_has_schema` / `risk_total_affected` are passed in).
   - Outputs ordered phases: Pre-Change Verification, Core Modifications, Blast Radius Adjustments, and Post-Change Regression Validation.

## Interfaces
- **Python API:** `GraphQueryEngine.compile_context(task, budget=1500, level=2, include_snippets=True) -> ContextPackage`
- Default pack: score each **file** once (entrypoint rank + blast membership, filename-stem boost for LoginPage/AuthContext), keep the top file plus only files within a relative band (`>= 0.5 * top`) under a 4-file cap — padding noise is trimmed to lift precision (dais: 0.33 → 0.79). A frontend recall backstop adds one best-matching client file when a client-side task kept none. `frontend_intent` needs an explicit client-side signal (not a bare "login"). A symmetric data/schema backstop (on `schema`/`create table`/`ddl`/`migration` intent) ensures every file defining a task-matched table — including tables defined via embedded SQL in Python — is in the pack, even across duplicate table names. Attach ~40-line spans, drop `ext:` stdlib, expand NL exclusions. `coverage: partial` when a frontend-intent task keeps no JS/TS file.
- Token-budget enforcement: when the rendered pack exceeds `budget`, shed surplus neighbor snippets → indirect → extra direct cards while keeping the primary entrypoint and one snippet per shortlisted file (dais packs now ≤ ~1.6k tokens).
- **CLI Commands:**
  - `repopeek --context "<task>" [--budget 1500] [--level 1|2|3] [--snippet]`
  - `repopeek --plan "<task>"`
