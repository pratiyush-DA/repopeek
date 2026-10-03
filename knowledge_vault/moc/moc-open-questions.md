---
id: moc-open-questions
type: moc
title: "Open Questions \u2014 Map of Content"
summary: All TBDs and ambiguities from source documents that require a human decision
  before implementation.
last_verified: 2026-10-03
affects: []
depends_on: ['[[adr-004-graph-persistence-tbd]]', '[[adr-005-python-parser-tbd]]']
---
# Open Questions — Map of Content

> Every unresolved ambiguity from the source docs lives here. Update status when resolved.

## Q1 — Graph persistence format
- **Status:** TBD
- **Note:** [[adr-004-graph-persistence-tbd]]
- **Source:** `_sources/mvp_requirements.md` §Graph persistence/output
- **Question:** Should the graph be exported as a JSON dump or SQLite database?
- **Impact:** Affects [[comp-graph]], [[feat-graph-persistence]], and how [[feat-query-cli]] reads data.

## Q2 — Python parser library
- **Status:** TBD
- **Note:** [[adr-005-python-parser-tbd]]
- **Source:** `_sources/mvp_requirements.md` §Python parsing
- **Question:** Use `tree-sitter` (richer AST, external dependency) or stdlib `ast` (simpler, built-in)?
- **Impact:** Affects [[comp-parsers]], [[feat-python-parser]].

## Q3 — Provenance commit field
- **Status:** TBD
- **Source:** `_sources/architecture_documentation.md` §4 Provenance
- **Question:** The `provenance_commit` field on semantic nodes is listed as TBD. How should git commit hashes be obtained and stored?
- **Impact:** Affects [[data-node-businessprocess]], [[data-node-story]], [[feat-provenance-binding]].

## Q4 — LLM connection
- **Status:** TBD
- **Source:** Not specified in any source document
- **Question:** Which LLM / SDK is used for semantic enrichment? How is the API key configured?
- **Impact:** Affects [[comp-enrichment]], [[feat-semantic-enrichment]].
