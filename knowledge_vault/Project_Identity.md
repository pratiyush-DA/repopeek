# Project Identity

#project #identity #scope #rules

## Overview
**Repopeek** is a Repository Intelligence / Semantic Code Property Graph (SCPG) system. It combines deterministic code relationships extracted directly from source code with high-level semantic/business understanding inferred by an LLM to serve as a persistent memory and impact analysis layer for AI coding agents.

## Core Directives & Boundaries
1. **Strict Separation of Concerns**: Strict separation between the deterministic code substrate ([[Deterministic_Substrate]]) and the LLM-inferred business overlay ([[Semantic_Overlay]]).
2. **Anti-Hallucination Policy**: If a behavior, schema field, dependency, architectural decision, or product requirement is not documented or directly inferable from existing code, do not invent it. Mark as `TBD` or clarify.
3. **Local & Lightweight**: Local execution using minimal dependencies (e.g., standard AST/tree-sitter, NetworkX, local JSON/SQLite persistence).
4. **Scope Enclosure**: Strictly prohibited for MVP:
   - Distributed graph databases (Neo4j, Memgraph, FalkorDB).
   - Kubernetes / cloud deployments.
   - Multi-tenant SaaS architecture.
   - Full IDE implementations or code generation engines.
   - Broad multi-language indexing beyond Python, SQL, and JSON.

## Related Documentation
- [[00_Index]]
- [[Architecture_Foundations]]
- [[Graph_Schema]]
- [[Milestones_and_Tasks]]
