# Security Constraints and Trust Boundaries

This document details the security constraints, filesystem isolation boundaries, API credential handling, and threat mitigations implemented across RepoPeek.

---

## 1. Filesystem Access Boundaries

### 1.1 Path Traversal Prevention
- **Constraint:** RepoPeek must strictly confine file reading and analysis to files located within the user-specified `--repo-path`.
- **Classification:** **Verified Invariant**.
- **Enforcement Mechanisms:**
  - [repopeek/discovery/crawler.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/crawler.py) resolves all paths against `repo_root.resolve()`.
  - Symlinks pointing outside the repository boundary are excluded during directory iteration to prevent path traversal vulnerability.

### 1.2 Exclusion of Sensitive Files and Secrets
- **Constraint:** The crawler must never ingest sensitive configuration files, API secrets, private keys, or credentials into the graph.
- **Classification:** **Verified Invariant**.
- **Evidence:** Enforced via crawler exclusion filters:
  - `.git/` (git object database and credentials).
  - `.env`, `.env.local`, `.env.production` (environment variables and API keys).
  - `*.pem`, `*.key`, `id_rsa` (cryptographic keys).
  - Secret patterns (`credentials.json`, `service_account.json`).

---

## 2. API Key and Credential Isolation

- **Constraint:** Cloud LLM credentials (`GROQ_API_KEY`) must never be leaked, persisted to disk, or serialized into graph artifacts.
- **Classification:** **Verified Invariant**.
- **Enforcement Mechanisms:**
  - `GROQ_API_KEY` is retrieved directly from `os.environ` inside [repopeek/llm/groq.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/llm/groq.py).
  - Configuration dumpers exclude API keys when writing `RepopeekConfig`.
  - Checksum manifests (`manifest.json`) and node cards never store environment variable values.
  - Logging masks or suppresses authentication headers.

---

## 3. Safe Deserialization Invariant

- **Constraint:** Loading graph artifacts from disk must never trigger arbitrary code execution.
- **Classification:** **Verified Invariant**.
- **Enforcement Mechanisms:**
  - Python's dangerous `pickle` module is strictly banned from persistence.
  - All graph files are loaded using Python's standard `json.loads()` and validated against Pydantic schemas.
  - SQLite databases are queried with parameterized SQL statements (`?` and `:named_param`), completely eliminating SQL injection risks.

---

## 4. Read-Only Query Safety

- **Constraint:** All query commands (`--lookup`, `--impact`, `--trace`, `--pack`, `--context`, `--plan`) and all 10 MCP tools must operate in strictly read-only mode.
- **Classification:** **Verified Invariant**.
- **Enforcement Mechanisms:**
  - The `GraphQueryEngine` exposes read-only methods.
  - SQLite connections are opened with `PRAGMA query_only = ON;`.
  - Source files are never modified, edited, or deleted by any query command or MCP tool.
