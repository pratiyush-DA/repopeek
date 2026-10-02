# MVP Requirements

## Objective
The MVP exists to prove that a repository can be analyzed into deterministic code relationships combined with semantic/business understanding, and represented in a local graph form that is queryable by an AI coding agent.

## In Scope
- Local repository file analysis.
- Python parsing (Framework choice: Proposed `tree-sitter`, exact implementation **TBD**).
- SQL parsing and analysis.
- JSON/configuration analysis.
- Deterministic extraction of code relationships (Calls, Imports, Reads).
- Local graph representation (Framework choice: Proposed `NetworkX`, exact implementation **TBD**).
- Semantic enrichment via LLM.
- Graph persistence/output (e.g., local JSON or SQLite, exact choice **TBD**).
- Basic CLI or programmatic ability to inspect/query the generated knowledge.

## Out of Scope (STRICTLY PROHIBITED FOR MVP)
- Neo4j, Memgraph, FalkorDB, or any distributed graph databases.
- Kubernetes or cloud deployments.
- Multi-tenant SaaS infrastructure.
- Enterprise authentication.
- Building a full IDE or a replacement coding agent.
- Broad multi-language support (10+ languages).
- Runtime distributed tracing / OpenTelemetry.
- Production-scale infrastructure.
- Advanced Git-diff incremental semantic updates.

## MVP Success Criteria
1. The system can inspect a small, local repository.
2. It mechanically identifies functions, queries, configs, and their structural relationships.
3. It represents these relationships accurately in a local graph.
4. It generates semantic descriptions grounded in source code.
5. Semantic information maintains provenance pointers back to source evidence.
6. A developer/agent can query the graph to understand a specific code path or impact tree.

## Non-Goals
This MVP is NOT attempting to write code, execute tests, or replace existing AI agents (like Cursor or Copilot). It is building a memory/index utility for them.

## Constraints
- Favor simple architecture and local execution.
- Maintain deterministic behavior wherever possible.
- Keep dependencies minimal.
- Ensure the output graph is easily inspectable (human-readable JSON or simple local DB).

## Future Possibilities (FUTURE / NOT MVP)
*Do not implement these in the current phase.*
- MCP (Model Context Protocol) Server integration.
- SCIP integration for robust multi-language references.
- Incremental Git-based graph synchronization.
- Distributed enterprise deployments.