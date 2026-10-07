# Testing Strategy and Execution

This document details the test harness, test categorization, execution commands, and critical fixture traps for RepoPeek.

---

## 1. Test Suite Overview

RepoPeek maintains a 25-suite automated test matrix under [tests/](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/) covering parsers, graph construction, mathematical blast radius propagation, progressive context compilation, and the MCP stdio interface.

- **Total Test Count:** ~197 in `tests/` (2026-10-06). Groq live completion may skip on HTTP 429.
- **Typical Execution Duration:** ~40–50 seconds.
- **Test Runner:** `pytest` **must** be pointed at `tests/`.

---

## 2. Test Execution Commands

### 2.1 Standard Execution
```bash
# Windows PowerShell
$env:PYTHONPATH = "."
.venv\Scripts\python -m pytest tests

# Linux / macOS
PYTHONPATH=. .venv/bin/pytest tests
```

### 2.2 Targeted Subsystem Execution
To iterate rapidly on a specific component without running the full 50-second suite:

```bash
# Run parser tests only
pytest tests/test_python_parser.py tests/test_typescript_parser.py

# Run mathematical blast radius tests
pytest tests/test_blast_radius.py

# Run MCP server integration tests
pytest tests/test_mcp_suite.py

# Run retrieval and context compiler tests
pytest tests/test_retrieval.py tests/test_context_compiler.py
```

### 2.3 Verbose Output with Failure Details
```bash
pytest tests -v --tb=short
```

---

## 3. Critical Fixture Trap: Bare `pytest` Collection

> [!WARNING]
> Never run bare `pytest` from the repository root without specifying `tests/`.

### The Problem
The repository contains a gitignored evaluation workspace at `testing/` (currently `testing/dais/`, previously `testing/da-assistant/`). Bare `pytest` recurses into those trees and collects foreign Django tests:

```text
ERROR collecting testing/.../tests/...
ModuleNotFoundError: No module named 'django'
```

### The Solution
Always invoke pytest targeting the tests folder explicitly:
```bash
python -m pytest tests
```
`pytest.ini` sets `testpaths = tests`. Dais MCP/context eval (not part of pytest): `python testing/dais/run_mcp_matrix.py` after an index in `testing/dais/repopeek`.

---

## 4. Test Suite Categorization

| Category | Test Files | What It Protects |
|---|---|---|
| **Parsers** | `test_python_parser.py`<br>`test_typescript_parser.py`<br>`test_polyglot_parsers.py` | AST extraction correctness, class/method identification, import resolution, and syntax error tolerance. |
| **Graph Construction** | `test_graph_builder_and_lenses.py`<br>`test_graph_persistence.py`<br>`test_schema.py` | NetworkX DiGraph creation, deterministic JSON serialization, 9 lenses, and atomic swap persistence. |
| **Bridges & Data Flow** | `test_http_bridge.py`<br>`test_data_flow_and_bridges.py` | Wildcard route normalization (`/api/users/:id`), fetch to backend handler mapping, def-use chains. |
| **Retrieval & Blast Radius** | `test_blast_radius.py`<br>`test_retrieval.py`<br>`test_retrieval_reliability.py`<br>`test_context_compiler.py` | Multi-path Noisy-OR formula, path decay, RRF ranking, budget-governed context packaging, and ChangePlan steps. |
| **External Protocols** | `test_mcp_suite.py`<br>`test_viewer_and_obsidian.py`<br>`test_watch_daemon.py` | 10 MCP JSON-RPC tools, HTTP viewer REST endpoints, Obsidian markdown export, `<50ms` watch sync. |
| **Enrichment & LLM** | `test_llm_provider.py`<br>`test_story_cascade.py`<br>`test_temporal_cochange.py` | Groq client mocking, 5-tier fallback cascade, FactVerifier hallucination rejection, git temporal co-changes. |
| **Golden End-to-End** | `test_golden_scenarios.py`<br>`test_evaluation.py` | End-to-end multi-language repositories, benchmark evaluation metrics (MRR, Brier score). |

---

## 5. Mocking and Network Isolation

All tests in `tests/` are completely isolated from external network dependencies:
- **Groq LLM Mocking:** Tests patch the Groq client or use `--offline` deterministic enrichment. No API keys or network calls are required during test execution.
- **Filesystem Isolation:** Dynamic file tests create isolated temporary directories via Pytest's `tmp_path` fixture.
- **Git Repository Fixtures:** Temporal miner tests dynamically initialize in-memory or temporary Git repositories with synthetic commits to test co-change mining deterministically.
