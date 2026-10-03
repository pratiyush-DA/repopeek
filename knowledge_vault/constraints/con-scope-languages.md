---
id: con-scope-languages
type: constraint
title: Supported Language Scope Restriction
summary: The MVP is strictly restricted to Python, SQL (Oracle dialect default), and
  JSON; all other languages are ignored.
status: active
tags: [constraint, scope, parsers]
affects: ['[[comp-discovery]]', '[[comp-parsers]]', '[[feat-file-classification]]']
last_verified: 2026-10-03
source: "_sources/cursorrules.md \xA7Scope Protection"
depends_on: []
---
# Supported Language Scope Restriction

## Rule
For the MVP release, Repopeek supports only three file formats:
1. Python (`.py`)
2. SQL (`.sql`, default Oracle dialect)
3. JSON (`.json`)

All other programming languages (JavaScript, TypeScript, Java, C++, Go, HTML, CSS, YAML, Markdown, etc.) must be safely ignored during discovery and classification without triggering errors.

## Rationale
Maintains razor-sharp focus on the target enterprise pipeline stack (Python ETL + Oracle PL/SQL + JSON configs) without premature multi-language parsing complexity.

## What it prohibits
- Adding Tree-Sitter parsers for languages outside Python/SQL/JSON during MVP.
- Failing discovery when encountering unknown file types in repository roots.

## Enforcement
- Handled directly in [[feat-file-classification]] via `supported_extensions` filter.

## Related
[[feat-file-classification]], [[comp-discovery]]
