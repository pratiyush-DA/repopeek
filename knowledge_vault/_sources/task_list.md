# Implementation Tasks

*Execution Rules:*
- Complete exactly one task at a time.
- Do not skip ahead.
- If a task requires an undocumented architectural decision, mark it as TBD and pause for clarification.
- Check off tasks `[x]` only when verified complete.

## Phase 1 — Project Foundation
*Purpose: Set up the local environment and project scaffolding.*
- [x] Step 1: Initialize project structure and Python environment.
- [x] Step 2: Add required MVP dependencies (e.g., AST parsers, local graph library).
- [x] Step 3: Create basic configuration and entry point script.

## Phase 2 — Repository Discovery
*Purpose: Traverse a local directory and classify files.*
- [ ] Step 4: Implement repository file discovery.
- [ ] Step 5: Classify supported file types (Python, SQL, JSON).

## Phase 3 — Python Analysis
*Purpose: Mechanically extract deterministic facts from Python code.*
- [ ] Step 6: Parse Python files (AST extraction).
- [ ] Step 7: Extract function definitions and line numbers.
- [ ] Step 8: Extract file imports.
- [ ] Step 9: Extract identifiable function calls.
- [ ] Step 10: Create deterministic Python graph nodes and edges (`File`, `Function`, `CALLS`, `IMPORTS`).

## Phase 4 — SQL Analysis
*Purpose: Extract deterministic facts from SQL files.*
- [ ] Step 11: Parse SQL files.
- [ ] Step 12: Extract identifiable queries and referenced tables.
- [ ] Step 13: Associate SQL nodes with relevant repository code (e.g., `READS` edges).

## Phase 5 — JSON Analysis
*Purpose: Extract deterministic facts from JSON configs.*
- [ ] Step 14: Parse JSON configuration files.
- [ ] Step 15: Represent relevant configuration relationships in the graph.

## Phase 6 — Graph Construction
*Purpose: Build and save the unified deterministic graph locally.*
- [ ] Step 16: Implement local graph data structures.
- [ ] Step 17: Validate generated graph against `docs/graph_schema.json`.
- [ ] Step 18: Persist/export the graph locally (e.g., JSON dump or SQLite).

## Phase 7 — Semantic Enrichment
*Purpose: Use an LLM to add business context overlaid on the deterministic graph.*
- [ ] Step 19: Define semantic enrichment input prompts and LLM connection.
- [ ] Step 20: Generate function-level summaries.
- [ ] Step 21: Generate higher-level semantic/business descriptions (`BusinessProcess`, `Story`).
- [ ] Step 22: Attach semantic nodes to deterministic graph nodes (`IMPLEMENTS`).
- [ ] Step 23: Ensure semantic data preserves provenance/confidence fields.

## Phase 8 — Query / Inspection
*Purpose: Provide a way to interact with the generated intelligence.*
- [ ] Step 24: Implement basic graph inspection CLI/functions.
- [ ] Step 25: Implement basic dependency/impact traversal (e.g., "What does this function impact?").
- [ ] Step 26: Demonstrate repository story reconstruction (e.g., "What business process does this file belong to?").

## Phase 9 — Validation
*Purpose: Prove the MVP Success Criteria are met.*
- [ ] Step 27: Create a small representative test repository.
- [ ] Step 28: Validate deterministic relationships are strictly accurate.
- [ ] Step 29: Validate semantic grounding and provenance.
- [ ] Step 30: Validate an end-to-end repository-to-graph workflow.