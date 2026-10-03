---
id: adr-011-mcp-interface
type: decision
title: Model Context Protocol (MCP) as External Query Interface
summary: Expose graph queries and context-packs via MCP for external AI agents, while
  keeping internal agent pipelines on typed Python calls.
status: accepted
tags: [architecture, mcp, integration, adr]
code_refs: []
depends_on: ['[[res-prior-art]]']
affects: ['[[feat-query-cli]]', '[[moc-decisions]]']
last_verified: 2026-10-03
source: "RepoPeek Owner Briefing \xA72 & \xA79"
---
# ADR-011: Model Context Protocol (MCP) as External Query Interface

## Status
Accepted

## Context
RepoPeek's target consumers are autonomous AI coding agents operating in low-context environments. The Model Context Protocol (MCP) is the emerging open standard for connecting LLM tools to external context providers. However, routing internal agent-to-agent communication through MCP would introduce serialization overhead and unnecessary network/process hops.

## Decision
1. **External Surface:** Expose RepoPeek's low-context retrieval layer as an official MCP server (`repopeek serve-mcp`), exposing tools:
   - `repopeek_lookup(query)`: Node card retrieval.
   - `repopeek_neighbors(node_id, depth)`: Bounded relational neighborhood.
   - `repopeek_impact(node_id)`: Blast radius and affected code/schema path.
   - `repopeek_data_trace(symbol)`: Variable/column flow.
   - `repopeek_context_pack(targets, token_budget)`: Budget-governed minimal context pack.
2. **Internal Architecture:** All internal stages (Scanner, Parsers, Resolver, Graph Builder) communicate exclusively via typed in-process Python objects (`asyncio` queues / function calls), never via internal MCP.

## Alternatives considered
- **Internal MCP microservices:** Rejected due to IPC latency and complexity.

## Consequences
- Clean separation between internal compute and external agent consumption.

## Notes
[[res-prior-art]], [[moc-decisions]]
