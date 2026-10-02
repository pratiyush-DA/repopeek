# Repopeek — Repository Intelligence Engine

Repopeek is a lightweight, local Semantic Code Property Graph (SCPG) engine designed to act as a persistent memory and impact analysis layer for AI coding agents.

## Core Capabilities
- **Deterministic Substrate**: Extracts syntactic facts (ASTs, functions, calls, imports, SQL queries, JSON configs) directly from source code.
- **Semantic Overlay**: Enriches deterministic graphs with LLM-grounded business narratives (`BusinessProcess`, `Story`).
- **Provenance Engine**: Binds every semantic inference back to exact file paths, line numbers, and confidence metrics.
- **Agent Protocol**: Provides graph traversal and impact tree extraction to enable safe, targeted code edits.

## Architecture & Documentation
Foundational specifications are located in the `docs/` directory:
- `docs/MVP_REQUIREMENTS.md`: Scope boundaries, constraints, and non-goals.
- `docs/ARCHITECTURE.md`: Pipeline architecture from ingestion to agent interface.
- `docs/graph_schema.json`: Graph node and edge schemas.
- `docs/TASKS.md`: Step-by-step milestone execution plan.

## Knowledge Vault
Learnings, decisions, and structural metadata are persistently tracked in the Obsidian vault at:
`/data/datafiles/mzp/uline_us_site/process/repo_intelligence_vault`
