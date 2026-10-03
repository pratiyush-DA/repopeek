---
id: moc-open-questions
type: moc
title: "Open Questions \u2014 Map of Content"
summary: Collected record of resolved architectural decisions and active implementation
  questions.
last_verified: 2026-10-03
affects: []
depends_on: ['[[adr-004-graph-persistence-tbd]]', '[[adr-005-python-parser-tbd]]']
---
# Open Questions — Map of Content

> Tracks architectural questions from inception to resolution.

## Resolved Questions (Owner Briefing)

### Q1 — Graph persistence format
- **Status:** Resolved (Accepted in [[adr-004-graph-persistence-tbd]])
- **Resolution:** Canonical format is sharded deterministic JSON. An optional SQLite index cache is permitted for fast recursive impact queries, subject to owner veto if JSON-only proves fast enough.

### Q2 — Python & multi-language parser library
- **Status:** Resolved (Accepted in [[adr-005-python-parser-tbd]])
- **Resolution:** Hybrid stack: tree-sitter for multi-language AST/CST and syntax-error tolerance, stdlib `ast` for high-fidelity Python passes, and `sqlglot` for SQL lineage. Benchmarks recorded in [[res-parsing-stack]].

### Q3 — Provenance commit field
- **Status:** Resolved (Accepted in [[adr-009-provenance-incremental-updates]])
- **Resolution:** Bind `repo_commit` (`git rev-parse HEAD`), dirty checkout flag, and per-file blob SHAs, with non-git fallback to content hashes.

### Q4 — LLM provider & API configuration
- **Status:** Resolved (Accepted in [[adr-006-llm-provider-abstraction]])
- **Resolution:** Initial provider is Groq via OpenAI-compatible endpoint, encapsulated behind the `LLMProvider` abstraction. Configured with abstract tiers (`fast`, `balanced`, `strong`).

---

## Active Phase 2 Investigation Items
1. **Benchmark Traversal Latency:** Measure whether SQLite index cache provides >5x speedup over streaming JSON on medium/large repos to decide if SQLite cache is retained or vetoed.
2. **Name Resolution Accuracy:** Benchmark Jedi vs tree-sitter symbol indexer for cross-file call target linking.
