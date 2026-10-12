---
id: feat-polyglot-engine
type: feature
title: Universal Polyglot Tree-Sitter Parser Engine
summary: Universal 36+ language code parsing engine utilizing Tree-Sitter grammars with transparent regex fallback and secret file shielding.
status: active
tags: [phase4, polyglot, tree-sitter, parsers]
code_refs: [repopeek/discovery/classifier.py, repopeek/parsers/polyglot.py, repopeek/graph/builder.py]
depends_on: ['[[comp-discovery]]', '[[comp-parsers]]', '[[plan-phase-4]]', '[[moc-features]]', '[[con-scope-languages]]']
affects: ['[[feat-graph-construction]]', '[[feat-graph-analysis]]', '[[feat-community-clustering]]']
last_verified: 2026-10-12
---

# Universal Polyglot Tree-Sitter Parser Engine

## Purpose
Enables deterministic AST extraction across 36+ programming languages (Go, Rust, Java, C, C++, C#, Ruby, PHP, Kotlin, Scala, Swift, Lua, Zig, PowerShell, Elixir, Erlang, Fortran, Julia, Objective-C, Verilog, Dart, Terraform, Solidity, Groovy, Pascal, Vue, Svelte, Astro, Markdown).

## Behavior / Contract
- `LanguageConfig`: Declarative configuration mapping AST node types (`class_types`, `function_types`, `import_types`, `call_types`) and regex fallback patterns.
- `PolyglotTreeSitterParser`: Dual-tier parser that dispatches to tree-sitter when installed, falling back cleanly to regex extraction when uninstalled.
- `is_sensitive_file`: Shields sensitive credentials (`.env`, `.key`, `.pem`, `id_rsa`, `.npmrc`, `.pypirc`) from discovery.
- Produces canonical `NodeCard`s and relational `Edge`s (`DEFINED_IN`, `CALLS`, `IMPORTS`).

## Impact
- **Depends on:** [[comp-discovery]], [[comp-parsers]], [[plan-phase-4]], [[moc-features]], [[con-scope-languages]]
- **Affects:** [[feat-graph-construction]], [[feat-graph-analysis]], [[feat-community-clustering]]

## Related
[[con-scope-languages]], [[moc-features]]
