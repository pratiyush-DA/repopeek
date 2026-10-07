# Dependency Analysis and Evaluation

This document details the external packages and standard library components utilized by RepoPeek, evaluating their architectural justification, version requirements, and alternatives.

---

## 1. Third-Party Dependencies Manifest

From [pyproject.toml](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/pyproject.toml#L20-L28):

```toml
dependencies = [
    "networkx>=3.0",
    "sqlglot>=25.0.0",
    "sqlparse>=0.5.0",
    "jsonschema>=4.20.0",
    "pydantic>=2.5.0",
    "pyyaml>=6.0.0",
    "ruamel.yaml>=0.18.0",
]
```

### Detailed Package Evaluation

| Package | Minimum Version | Primary Modules Using It | Justification | Trade-offs & Risks |
|---|---|---|---|---|
| **`networkx`** | `>=3.0` | `repopeek/models/schema.py`<br>`repopeek/graph/builder.py`<br>`repopeek/analysis/blast_radius.py` | Mature graph data structures (`DiGraph`), cycle detection, and topological sorting algorithms. | High memory overhead for multi-million-node graphs; mitigated by storing lightweight IDs and coordinates. |
| **`sqlglot`** | `>=25.0.0` | `repopeek/parsers/sql.py` | Accurate multi-dialect SQL AST parser supporting Oracle, Postgres, Snowflake, and BigQuery dialects. | Complex expression hierarchy; fallback to `sqlparse` handles dialect-specific syntax irregularities. |
| **`sqlparse`** | `>=0.5.0` | `repopeek/parsers/sql.py` | Robust lexical tokenizer that never fails on non-standard SQL syntax. | Does not build a semantic tree; used exclusively as a resilient fallback parser. |
| **`jsonschema`** | `>=4.20.0` | `repopeek/config.py`<br>`repopeek/query/mcp_server.py` | Validates MCP tool parameter payloads against JSON schema drafts. | Minimal overhead; standard Python JSON schema validator. |
| **`pydantic`** | `>=2.5.0` | `repopeek/models/schema.py`<br>`repopeek/storage/json_store.py` | Core data model validation, typed serialization, and high-performance Rust-backed JSON dumping. | Requires Pydantic v2 API (`model_validate`, `model_dump`); v1 compatibility is unsupported. |
| **`pyyaml`** | `>=6.0.0` | `repopeek/parsers/docker.py`<br>`repopeek/parsers/yaml_config.py` | Fast YAML document parsing for Docker Compose and Kubernetes manifests. | Uses safe loader (`yaml.safe_load`) to prevent code execution vulnerabilities. |
| **`ruamel.yaml`** | `>=0.18.0` | `repopeek/parsers/yaml_config.py` | Round-trip YAML parser preserving exact comments, key ordering, and formatting. | Slightly slower than C-accelerated PyYAML, but essential for preserving configuration integrity. |

---

## 2. Standard Library Utilization

Following the **Ponytail Protocol**, RepoPeek aggressively leverages Python's built-in standard library to minimize dependency bloat:

- **`ast`:** Complete, zero-dependency Python syntax tree parsing, docstring extraction, complexity analysis, and import mapping.
- **`sqlite3`:** Embedded relational database and FTS5 full-text indexing for sub-millisecond query acceleration without external services.
- **`pathlib`:** Object-oriented, robust path resolution and manipulation across Windows, macOS, and Linux.
- **`http.server` & `urllib.parse`:** Embedded HTTP server for the interactive web viewer without needing Flask, FastAPI, or Uvicorn.
- **`hashlib`:** Cryptographic SHA-256 calculation for file change detection and deterministic graph verification.
- **`json`:** Fast deterministic serialization with key sorting.
- **`re`:** High-performance regular expressions powering the TypeScript/JavaScript AST state machine.
- **`threading`:** Lightweight background daemon polling and web server concurrency.

---

## 3. Dependency Vulnerability and Supply Chain Security

- **Pinned Ranges:** All dependencies declare conservative minimum versions (`>=`) to prevent dependency conflicts while ensuring modern, patched releases.
- **Zero Binary Compilation:** Every production dependency provides universal pure-Python wheels or widely distributed platform wheels, guaranteeing seamless installation on Windows, Linux, and macOS.
- **Strictly Scoped Development Dependencies:** Test tools (`pytest>=7.0.0`) are isolated in `[project.optional-dependencies].dev` and never installed in production container environments.
