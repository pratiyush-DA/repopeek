---
id: feat-typescript-parser
type: feature
title: TypeScript & JavaScript Polyglot AST Parser
summary: Deterministic lexical and syntactic AST parser extracting classes, methods, functions (incl. hook/HOC-wrapped arrows), SCREAMING_SNAKE module constants, interfaces, types, imports, and calls for .ts, .tsx, .js, .jsx files.
status: verified
tags: [parser, typescript, javascript, polyglot, ast]
code_refs: [repopeek/parsers/typescript.py, repopeek/discovery/classifier.py, repopeek/graph/builder.py, repopeek/graph/resolver.py, tests/test_typescript_parser.py]
depends_on: ['[[comp-parsers]]', '[[feat-graph-construction]]', '[[plan-phase-3]]']
affects: ['[[log-phase-3]]', '[[feat-http-bridge]]']
last_verified: 2026-10-06
---

# TypeScript & JavaScript Polyglot AST Parser

## 1. Executive Summary & Purpose
Provides offline, deterministic lexical and syntactic parsing of TypeScript (`.ts`, `.tsx`, `.mts`, `.cts`) and JavaScript (`.js`, `.jsx`, `.mjs`, `.cjs`) codebases. Extracts canonical `NodeCard` structures (files, classes, methods, functions, interfaces, type aliases) and typed `Edge`s (`IMPORTS`, `DEFINED_IN`, `CALLS`, `INHERITS`, `IMPLEMENTS`) with exact character and line spans without requiring Node.js or heavy external C-extensions.

## 2. Core Architectural Design & Capabilities
1. **Zero-Dependency Resilient Lexical Pipeline:**
   - Multi-pass source analyzer operating on Python stdlib (`re`, `bisect`, `pathlib`).
   - String and comment neutralizer preserving exact newline offsets so character spans map 1-to-1 to original code.
   - JSDoc comment harvester associating `/** ... */` documentation blocks with following symbols.
2. **Structural Symbol Extraction:**
   - **Imports & Re-exports:** Handles ES6 named/default/aliased imports (`import { a, b as c } from './mod'`), bare imports, dynamic `import()`, and CommonJS `require()`.
   - **Interfaces & Types:** Extracts `interface` definitions with `extends` inheritance and `type` aliases.
   - **Classes & Inheritance:** Extracts ES6/TypeScript classes, constructor, methods, getters/setters, `extends` base classes, and `implements` interfaces.
   - **Functions:** Standalone functions, async functions, variable-assigned arrow functions (`const fn = (...) => ...`), and arrow functions wrapped in React hooks/HOCs (`const login = useCallback(async (...) => {...}, [])`, `useMemo`, `memo`, `forwardRef`).
   - **Module constants:** SCREAMING_SNAKE_CASE module-level constants (`API_BASE_URL`, `REMEMBER_ME_DAYS`) are emitted as `variable` nodes so task-referenced config symbols are retrievable. Scoped to all-caps names to stay bounded (no node per local variable).
3. **Fact & Metric Extraction:**
   - Cyclomatic complexity computed deterministically from branch keywords and logical operators.
   - Exception discovery tracking `throw` statements into `facts.raises`.
   - HTTP endpoint call detection capturing `fetch(...)` and `axios` client invocations into `facts.reads` (e.g. `HTTP:/api/users`).
4. **Cross-File Symbol Resolution:**
   - `SymbolResolver` supports `.ts`, `.tsx`, `.js`, `.jsx` extensions and relative path navigation (`./`, `../`).
   - Resolves cross-file imports and call edges directly to target symbol `NodeCard`s with `Confidence.RESOLVED`.
