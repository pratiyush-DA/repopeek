---
id: con-scope-languages
type: constraint
title: Supported Language Scope Restriction
summary: MVP languages are Python, TypeScript/JavaScript, SQL, shell, JSON/YAML; other languages are ignored.
status: active
tags: [constraint, scope, parsers]
affects: ['[[comp-discovery]]', '[[comp-parsers]]', '[[feat-file-classification]]']
last_verified: 2026-10-06
source: "_sources/cursorrules.md \xA7Scope Protection"
depends_on: []
---
# Supported Language Scope Restriction

## Rule
Repopeek officially supports:
1. Python (`.py`, `.pyi`)
2. SQL (`.sql`, default Oracle dialect)
3. Shell (`.sh`, `.bash`)
4. Configs (`.json`, `.yaml`, `.yml`)
5. TypeScript (`.ts`, `.tsx`, `.mts`, `.cts`)
6. JavaScript (`.js`, `.jsx`, `.mjs`, `.cjs`)

All other programming languages (Java, C++, Go, HTML, CSS, Markdown, etc.) are safely ignored during discovery and classification without triggering errors.

## Rationale
Maintains razor-sharp focus on the target enterprise pipeline stack (Python ETL + Oracle PL/SQL + JSON configs) without premature multi-language parsing complexity.

## What it prohibits
- Adding Tree-Sitter parsers for languages outside Python/SQL/JSON during MVP.
- Failing discovery when encountering unknown file types in repository roots.

## Enforcement
- Handled directly in [[feat-file-classification]] via `supported_extensions` filter.

## Related
[[feat-file-classification]], [[comp-discovery]]
