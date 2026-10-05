# Changelog
*Append-only. One line per vault update: `YYYY-MM-DD | notes touched | reason`*

2026-10-03 | vault scaffolded, _sources copied, templates created, conventions written | initial vault setup per protocol
2026-10-03 | 48 atomic notes written, 5 MOCs, 00-index.md, moc-open-questions.md, validate.py, AGENTS.md | complete graph-structured vault implementation and reciprocity verification
2026-10-03 | Phase-2 plan/log, ADR-006 to ADR-012, ADR-004/005 updates, 4 research notes, node-card-spec, lenses, runbook | Phase 2 kickoff, owner decisions recorded, research completed, vault documentation updated
2026-10-03 | comp-discovery, feat-file-discovery, feat-file-classification, Phase-2/log, pyproject.toml | PR 2 scanner agent, canonical schema models, and fixture repo implementation
2026-10-03 | comp-parsers, feat-python-parser, Phase-2/log | PR 3 Python AST parser with resilient fallback and embedded SQL extraction
2026-10-03 | comp-parsers, feat-sql-parser, feat-json-parser, Phase-2/log | PR 4 Polyglot Parsers (SQL, Shell, JSON, YAML) with Ponytail full mode
2026-10-03 | comp-graph, feat-graph-construction, Phase-2/log | PR 5 Symbol resolution, GraphBuilder, and multi-lens projections
2026-10-03 | comp-graph, data-graph-lenses, Phase-2/log, _meta/changelog | PR 6 Def-use data flow, config readers, cross-language bridges, and specialized lenses
2026-10-03 | comp-graph, feat-graph-persistence, Phase-2/log, _meta/changelog | PR 7 Deterministic graph persistence, Git provenance, and SQLite traversal cache
2026-10-04 | comp-enrichment, Phase-2/log, _meta/changelog | PR 8 LLM provider abstraction, Groq adapter with live inference, mock and fallback providers
2026-10-04 | comp-enrichment, feat-semantic-enrichment, Phase-2/log, _meta/changelog | PR 9 Story cascade, content-hash cache, fact verifier, and cost governor
2026-10-04 | comp-query, feat-query-cli, Phase-2/log, _meta/changelog | PR 10 Low-context retrieval, context-pack service, and stdio MCP server
2026-10-04 | Phase-2/plan, Phase-2/log, _meta/changelog | PR 11 Dogfooding on RepoPeek repository, golden scenarios validation, and CLI/MCP polish
2026-10-04 | feat-graph-persistence, feat-query-cli, _meta/changelog | Interactive graph viewer and Obsidian Markdown vault exporter/reader
2026-10-04 | feat-graph-persistence, feat-query-cli, _meta/changelog | Obsidian vault auto-detection (%APPDATA%), obsidian:// URI dispatch via --open, and .gitignore exclusions
2026-10-04 | feat-query-cli, feat-graph-persistence, data-node-card-spec, _meta/changelog | Ultra-low context optimizations: in-card snippet extraction (--snippet), facts truncation, 1-hop blast radius, and incremental single-file update (--update)
2026-10-05 | Phase-3/plan, Phase-3/log, 00-index, _meta/changelog | Phase 3 Context Compiler & Blast Radius Engine roadmap initialization
2026-10-05 | feat-intent-retrieval, moc-features, Phase-3/plan, Phase-3/log, _meta/changelog | PR 12 Intent-to-Symbol Task Matcher, SQLite FTS5 BM25 Index, and RRF rank fusion
2026-10-05 | feat-traversal-confidence, moc-features, Phase-3/plan, Phase-3/log, _meta/changelog | PR 13 Mathematical Traversal Confidence, Multi-Path Reinforcement, and Blast Radius Partitioning
2026-10-05 | feat-context-compiler, moc-features, Phase-3/plan, Phase-3/log, _meta/changelog | PR 14 Context Compiler, Constraint Extractor & Change Plan Generator
2026-10-05 | feat-typescript-parser, comp-parsers, feat-graph-construction, moc-features, con-scope-languages, Phase-3/plan, Phase-3/log, _meta/changelog | PR 15 Polyglot Expansion: TypeScript & JavaScript Parser
2026-10-05 | feat-git-temporal, feat-graph-construction, moc-features, Phase-3/plan, Phase-3/log, _meta/changelog | PR 16 Git Temporal Intelligence & Co-Change Matrix
2026-10-05 | feat-http-bridge, feat-python-parser, feat-typescript-parser, feat-graph-construction, moc-features, Phase-3/plan, Phase-3/log, _meta/changelog | PR 17 Cross-Language HTTP Boundary Bridge
2026-10-05 | feat-agent-mcp, feat-watch-daemon, feat-query-cli, feat-context-compiler, feat-traversal-confidence, feat-graph-persistence, feat-graph-construction, moc-features, Phase-3/plan, Phase-3/log, _meta/changelog | PR 18 Agent MCP Suite & Incremental Watch Daemon (Phase 3 Complete)
2026-10-05 | feat-evaluation-benchmarking, moc-features, Phase-3/plan, Phase-3/log, _meta/changelog | PR 19 Agent Evaluation & Benchmarking Subsystem (4 levels, 50 frozen tasks, calibration, and token reduction)
2026-10-05 | feat-intent-retrieval, feat-traversal-confidence, feat-evaluation-benchmarking, _meta/changelog | PR 20 Reliability overhaul: linguistic stemming, 6-casing variants, multi-component ranking, hard negative pruning, inverted index acceleration, Recall@5 26%->80%, MRR 0.22->0.75



