---
name: repopeek
description: Repository Intelligence and Semantic Code Property Graph Engine. Use to query symbols, blast radius, change plans, modular communities, god nodes, and wiki reports.
triggers:
  - repopeek
  - /repopeek
  - codebase graph
  - blast radius
  - code topology
---

# RepoPeek Agent Skill

RepoPeek provides deterministic, low-context codebase property graphs, topological analysis, and context compilation for AI coding agents.

## Core Directives for Coding Agents
1. **Never read monolithic files blindly**: Query RepoPeek via CLI or MCP to obtain exact node cards and targeted snippets (<80 tokens).
2. **Blast Radius Verification**: Before editing a shared class or function, run `--impact` or `repopeek_impact` to assess upstream consumers and callers.
3. **Change Planning**: When planning non-trivial edits, run `--plan` or `repopeek_plan` to generate an indexed, risk-assessed change plan.
4. **Architectural Understanding**: Consult `repopeek-out/GRAPH_REPORT.md` and `repopeek-out/wiki/index.md` for modular community structures and god nodes.

## Command Reference

### 1. Architectural Auditing & Reports
```bash
# Generate full human/agent markdown audit report
repopeek report [--out repopeek-out/GRAPH_REPORT.md]

# Generate Wikipedia-style agent documentation wiki
repopeek wiki [--out repopeek-out/wiki]

# Detect unsupervised modular communities with cohesion scores
repopeek cluster

# Run topological analysis (god nodes, cycles, surprising edges, questions)
repopeek analyze

# Standalone visualizer & exports
repopeek export html      # writes repopeek-out/graph.html
repopeek export obsidian  # writes repopeek-out/obsidian
repopeek export json      # writes repopeek-out/graph.json
```

### 2. Targeted Querying & Edits
```bash
# Look up a code entity with its exact source code snippet for zero-file-read edits
repopeek --lookup <symbol_or_id> --snippet

# Calculate upstream and downstream blast radius
repopeek --impact <symbol_or_id>

# Compile a budget-governed context package for an engineering task
repopeek --context "<natural language task>" --budget 1500 --level 2

# Generate a risk-assessed change plan
repopeek --plan "<task>"

# Start Stdio MCP Server
repopeek --serve-mcp
```

### 3. MCP Tools (When running as stdio server)
- `repopeek_context`: Task-to-context compiler with progressive disclosure.
- `repopeek_plan`: Risk-assessed engineering change plan.
- `repopeek_impact`: Traversal blast radius.
- `repopeek_god_nodes`: Core architectural hubs and degree centrality.
- `repopeek_cycles`: Detect circular dependency chains.
- `repopeek_communities`: Partition code into functional clusters.
- `repopeek_suggest_questions`: Generate actionable architecture questions.
- `repopeek_report`: Produce complete Markdown audit trail.
- `repopeek_lookup`: Direct symbol lookup with snippets.
- `repopeek_neighbors`: Direct inbound/outbound relational edges.
