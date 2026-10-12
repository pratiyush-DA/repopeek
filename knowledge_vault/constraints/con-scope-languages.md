---
id: con-scope-languages
type: constraint
title: Supported Language Scope Restriction
summary: Universal support for 36+ languages via specialized parsers and the polyglot Tree-Sitter engine; secret files shielded.
status: active
tags: [constraint, scope, parsers, polyglot]
affects: ['[[comp-discovery]]', '[[comp-parsers]]', '[[feat-file-classification]]', '[[feat-polyglot-engine]]']
last_verified: 2026-10-12
source: "_sources/cursorrules.md §Scope Protection; Phase 4 Polyglot Roadmap"
depends_on: []
---
# Supported Language Scope Restriction

## Rule
Repopeek supports universal code property graph extraction across 36+ languages:
1. Core AST: Python, SQL (Oracle/Postgres/MySQL/SQLite), Shell/Bash, JSON, YAML, TypeScript, JavaScript
2. Systems & Compiled: Go, Rust, Java, Kotlin, Scala, Groovy, C, C++, C#, Swift, Zig, Pascal
3. Dynamic & Scripting: Ruby, PHP, Lua, PowerShell, Elixir, Erlang, Julia, Dart
4. Scientific & Hardware: Fortran, Verilog, SystemVerilog
5. Infrastructure & Docs: Terraform/HCL, Solidity, Vue, Svelte, Astro, Markdown

Sensitive credential files (`.env`, `.key`, `.pem`, `id_rsa`, `.npmrc`) are shielded from indexing.

## Rationale
Universal polyglot coverage with zero external database dependencies enables comprehensive repository intelligence across modern multi-language monorepos and polyglot architectures.

## Enforcement
- Handled directly in [[feat-file-classification]] and [[feat-polyglot-engine]].

## Related
[[feat-file-classification]], [[comp-discovery]], [[feat-polyglot-engine]]
