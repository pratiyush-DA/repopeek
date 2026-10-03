---
id: adr-005-python-parser-tbd
type: decision
title: Python Parser Engine Selection (Pending Decision)
summary: Evaluate Python standard library ast module vs tree-sitter for deterministic
  parsing; decision currently TBD.
status: proposed
tags: [architecture, python, parser, open-question, adr]
affects: ['[[comp-parsers]]', '[[feat-python-parser]]', '[[moc-open-questions]]']
last_verified: 2026-10-03
source: "_sources/task_list.md \xA7Phase 3"
depends_on: []
---
# ADR-005: Python Parser Engine Selection (Pending Decision)

## Status
Proposed (Pending Decision)

## Context
Deterministic Python parsing requires extracting function definitions, line ranges, function calls, and import statements. We must choose between the built-in Python `ast` module and `tree-sitter`.

## Decision
Decision is currently marked **TBD**. The initial baseline for Phase 3 prototyping is Python's standard library `ast` module due to zero external dependencies and exact line-number accuracy. `tree-sitter` is under evaluation for error-tolerant parsing of partially broken files.

## Alternatives considered
- **Python stdlib `ast`:**
  - *Pros:* Built into Python stdlib; zero external C/wheel dependencies; robust `ast.NodeVisitor` and `ast.walk`; 100% compliant with host Python syntax.
  - *Cons:* Fails on invalid Python syntax (syntax error aborts parse); restricted to syntax supported by the running Python runtime.
- **Tree-sitter (`tree-sitter-python`):**
  - *Pros:* Error-tolerant (parses invalid/partial code); unified AST representation across languages.
  - *Cons:* Binary wheels and native C compilation required; higher dependency maintenance.

## Consequences
- Tracked in [[moc-open-questions]] until finalized in Phase 3.

## Notes
[[feat-python-parser]], [[moc-open-questions]], [[moc-decisions]]
