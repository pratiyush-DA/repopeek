---
id: adr-005-python-parser-tbd
type: decision
title: Hybrid Multi-Language Parsing Stack (Tree-Sitter + AST + SQLGlot)
summary: Adopt a hybrid parsing stack using tree-sitter for multi-language syntax
  and error recovery, stdlib ast for high-fidelity Python passes, and SQLGlot for
  SQL.
status: accepted
tags: [architecture, parsers, tree-sitter, ast, adr]
code_refs: [repopeek/parsers/]
depends_on: ['[[res-parsing-stack]]']
affects: ['[[comp-parsers]]', '[[feat-python-parser]]', '[[moc-decisions]]', '[[moc-open-questions]]']
last_verified: 2026-10-03
source: "RepoPeek Owner Briefing \xA72 & \xA73.1; [[res-parsing-stack]]"
---
# ADR-005: Hybrid Multi-Language Parsing Stack (Tree-Sitter + AST + SQLGlot)

## Status
Accepted

## Context
Codebases under analysis contain multiple languages (Python, SQL, Shell, JSON, YAML) and often include WIP files or invalid syntax. Python's standard library `ast` provides exact semantics but immediately aborts on syntax errors and cannot parse Bash or SQL. Conversely, tree-sitter provides error-tolerant Concrete Syntax Trees (CSTs) across languages but does not perform Python semantic validation.

## Decision
Adopt a **Hybrid Parsing Strategy**:
1. **Multi-Language Baseline:** Use `tree-sitter` (via `tree-sitter-python` and `tree-sitter-bash`) as the primary error-tolerant parser across Python, shell, and other structural files.
2. **High-Fidelity Python Pass:** For syntactically valid `.py` files, run stdlib `ast` to extract comprehensive Python semantics (decorators, async generators, comprehensions, context managers, exception scopes). If syntax errors occur, fall back to tree-sitter's error-tolerant tree and mark the file with `parse_status: "syntax_error"` while preserving partial nodes.
3. **SQL Lineage:** Use `sqlglot` with `dialect="oracle"` for all `.sql` files and SQL string literals extracted from Python.
4. **Configuration Extraction:** Use stdlib `json` and `ruamel.yaml` to extract schema structures and exact keypath line spans.

## Alternatives considered
- **Pure `ast`:** Rejected because it completely breaks on partial/syntax-error files and cannot handle non-Python code.
- **Pure `tree-sitter` without `ast`:** Feasible, but stdlib `ast` provides faster, richer metadata for Python-specific features without custom grammar query maintenance.

## Consequences
- Error-tolerant: partial files still produce nodes and edges.
- High precision: valid Python code gets full semantic depth.

## Notes
[[feat-python-parser]], [[res-parsing-stack]], [[moc-decisions]]
