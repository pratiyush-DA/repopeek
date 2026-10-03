---
id: log-phase-2
type: log
title: Phase 2 Decision and Execution Log
summary: Running chronological log of decisions, research findings, dead ends, and
  open questions during Phase 2.
status: active
tags: [phase2, log, decisions]
code_refs: []
depends_on: ['[[plan]]']
affects: []
last_verified: 2026-10-03
---
# Phase 2 Decision and Execution Log

## 2026-10-03: Phase 2 Kickoff & Scope Alignment
- **Event:** Briefing received from repository owner.
- **Git State:** Verified existing commits on branch `main`; configured remote origin `https://github.com/pratiyush-DA/repopeek.git`.
- **MCP Integration:** Selected and configured `@modelcontextprotocol/server-github` in `~/.gemini/config/mcp_config.json`.
- **Decisions Recorded:**
  - ADR-004 updated: Canonical JSON selected for graph persistence.
  - ADR-005 updated: Tree-sitter + stdlib AST hybrid approach designated for benchmark.
  - LLM Provider: Modular Groq / OpenAI-compatible abstraction.
  - Languages expanded: Python, SQL, Shell, JSON, YAML.
- **Next Immediate Action:** Execute research and benchmarks for parsing stack, prior art, Groq cost parameters, and storage performance.

## 2026-10-03: PR 2 — Scanner Agent & Canonical Schema Implemented
- **Canonical Schema:** Implemented `NodeCard`, `NodeFacts`, `NodeStory`, `NodeProvenance`, `Span`, `Edge`, `EdgeType`, `Confidence`, and `CanonicalGraph` in `repopeek/models/schema.py`.
- **Scanner Engine:** Implemented deterministic repository discovery in `repopeek/discovery/`:
  - `crawler.py`: Recursive walker with sorted traversal and directory pruning.
  - `classifier.py`: Extension mapping, shebang fallback, binary detection.
  - `hasher.py`: Deterministic content SHA-256 and standard Git blob SHA calculation.
  - `ignore.py`: Pattern matcher for `.repopeekignore` with trailing slash / directory glob support.
- **Fixture Repository:** Created golden testbed in `tests/fixtures/sample_repo/` covering Python inheritance, calls, embedded SQL, syntax error, Oracle PL/SQL, shell script, JSON config, YAML pipeline, and ignored files.
- **CLI Connection:** Connected scanner agent to `repopeek` CLI command.
- **Testing:** 20/20 unit tests green.

## 2026-10-03: PR 3 — Python Parser Agent Implemented
- **Base Parser:** Implemented `BaseParser` and `ParseResult` dataclass in `repopeek/parsers/base.py`.
- **Python AST Engine:** Implemented `PythonParser` in `repopeek/parsers/python.py`:
  - AST-driven fact extraction: parameters, returns, cyclomatic complexity, reads, writes, raises, calls.
  - Line span boundaries (`Span`) and SHA-256 source slice hashing.
  - Embedded SQL query extraction via SQL regex detection producing `sql_query` NodeCards and `EMBEDS_SQL` edges.
  - Class inheritance extraction with `INHERITS` and `DEFINED_IN` edges.
- **Resilient Fallback:** Implemented fallback regex scanner for broken syntax (`SyntaxError`), recovering partial function, class, and import definitions with `Confidence.UNRESOLVED` without crashing.
- **Testing:** 25/25 unit tests green across complete test suite.

## 2026-10-03: Ponytail Configuration & Verification
- **Installation:** Installed official `DietrichGebert/ponytail` extension via native Antigravity CLI (`agy plugin install https://github.com/DietrichGebert/ponytail`). Verified via `agy plugin list` (active components: skills, commands).
- **Workspace Rule & Protocol:** Configured `.agents/rules/ponytail.md` and updated `AGENTS.md` with active `full` mode.
- **Constraints Applied:** Enforced YAGNI -> codebase reuse -> stdlib first -> existing deps -> minimal correct implementation. Preserved all error handling, validation, and test requirements.

## 2026-10-03: PR 4 — Polyglot Parsers Implemented
- **SqlParser (`repopeek/parsers/sql.py`):**
  - Utilizes `sqlglot` with Oracle dialect default and Postgres/ANSI fallback.
  - Extracts table definition NodeCards (`sql_table`) and columns with `DEFINED_IN` edges.
  - Extracts query NodeCards (`sql_query`), referenced tables/columns (`READS` edges), and write targets (`WRITES` edges).
  - Resilient fallback regex extraction for malformed SQL without crashing.
- **ShellParser (`repopeek/parsers/shell.py`):**
  - Utilizes standard library `shlex` and regex.
  - Extracts command NodeCards, command pipelines, environment variables written (`WRITES`) and read (`READS`).
  - Detects executed script targets (`python script.py`, `bash script.sh`) and emits `RUNS_SCRIPT` edges.
- **Config Parsers (`repopeek/parsers/config.py`):**
  - `JsonConfigParser` using standard library `json`. Flattens nested keys (`json_config` NodeCards) and handles decode errors gracefully.
  - `YamlConfigParser` using `yaml`. Flattens nested keys (`yaml_config` NodeCards), detects script execution references (`RUNS_SCRIPT` edges), and handles syntax errors gracefully.
- **Testing:** Added `tests/test_polyglot_parsers.py`. Test suite increased to 35/35 passing unit tests.

