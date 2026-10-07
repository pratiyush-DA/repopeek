# Technical Constraints

This document details the environment requirements, language limits, path representations, and schema constraints enforced by RepoPeek.

---

## 1. Runtime and Language Requirements

### 1.1 Python Version Compatibility
- **Constraint:** Requires Python $\ge 3.10$.
- **Classification:** **Verified Invariant**.
- **Evidence:** Enforced in [pyproject.toml](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/pyproject.toml#L10) (`requires-python = ">=3.10"`). The codebase relies on Python 3.10 structural pattern matching (`match/case`) and union operator type syntax (`int | None`). Attempting to execute with Python 3.9 or earlier results in a syntax error during AST compilation.

### 1.2 Zero Native Compilation
- **Constraint:** RepoPeek must run purely on standard Python without requiring C, C++, or Rust build tools (e.g. gcc, clang, MSVC, cargo).
- **Classification:** **Verified Invariant**.
- **Evidence:** All dependencies (`networkx`, `sqlglot`, `sqlparse`, `pydantic`, `pyyaml`, `ruamel.yaml`) provide pre-built pure-Python wheels or universal binaries. No tree-sitter or native extensions are included.

---

## 2. Path Normalization and Cross-Platform Portability

### 2.1 POSIX Slash Normalization
- **Constraint:** All internal node IDs, relative file paths, and `Span.file` values must strictly use forward slashes (`/`), even when executed on Microsoft Windows.
- **Classification:** **Verified Invariant**.
- **Evidence:** Enforced in [repopeek/models/schema.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py) via field validators and [repopeek/discovery/crawler.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/crawler.py#L42):
  ```python
  rel_path = str(file_path.relative_to(root)).replace("\\", "/")
  ```
- **Rationale:** Ensures that a graph indexed on Windows produces identical node IDs and hashes when queried on Linux or in a cloud CI runner.

### 2.2 Case Sensitivity Invariant
- **Constraint:** File paths inside node IDs preserve the casing of the filesystem.
- **Classification:** **Strong Convention**.
- **Evidence:** Path strings are converted via `str(path)`, which on Windows preserves original case. Symbol resolution relies on case-exact lookup dictionaries.

---

## 3. Schema and Protocol Compatibility

### 3.1 CanonicalGraph Versioning
- **Constraint:** All persisted `graph.json` and `manifest.json` files must declare `schema_version = "1.0.0"`.
- **Classification:** **Verified Invariant**.
- **Evidence:** Enforced by default fields in [repopeek/models/schema.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py#L133). Deserializers check `schema_version` and raise errors on major version increments.

### 3.2 UTF-8 File Encoding
- **Constraint:** All source code reads, AST token streams, JSON disk writes, and SQLite connections must explicitly declare and enforce UTF-8 encoding.
- **Classification:** **Verified Invariant**.
- **Evidence:** Enforced across all I/O calls:
  ```python
  target_path.write_text(serialized, encoding="utf-8")
  ```
  Prevents platform-default encoding crashes (such as Windows `cp1252` encountering Unicode characters in source files).
