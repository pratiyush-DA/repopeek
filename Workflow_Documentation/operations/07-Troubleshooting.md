# Troubleshooting and Diagnostic Runbooks

This document provides diagnostic runbooks for resolving common operational anomalies, build errors, test failures, and performance traps encountered in RepoPeek.

---

## 1. Pytest Collection Error (`ModuleNotFoundError: No module named 'django'`)

### Symptoms
Running `pytest` from the workspace root produces:
```text
ERROR collecting testing/da-assistant/backend/tests/test_agent_api.py
ModuleNotFoundError: No module named 'django'
```

### Root Cause
Bare `pytest` automatically crawls the entire repository tree, discovering the real-world evaluation workspace located at `testing/da-assistant/`. That directory contains an external test suite designed for an independent Django/FastAPI backend, which requires dependencies not installed in RepoPeek's development environment.

### Remediation
Always invoke pytest targeting RepoPeek's test directory explicitly:
```bash
python -m pytest tests
```
Or specify the target suite:
```bash
pytest tests/test_retrieval.py
```

---

## 2. Unresolved Symbols or Missing Nodes in Graph

### Symptoms
Running `repopeek --lookup "MyFunction"` returns empty or `NodeCard not found`, even though the function exists in the codebase.

### Diagnostic Steps
1. **Check Extension Support:** Verify the file extension is registered in [repopeek/discovery/classifier.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/classifier.py#L12) under `SUPPORTED_TYPES`.
2. **Check Git Exclusions:** Inspect `.gitignore`. If the file is in a directory like `build/`, `dist/`, or `.cache/`, the crawler skips it by design.
3. **Check Dynamic Constructs:** Python `importlib.import_module()`, `eval()`, or JavaScript dynamic `require(variable)` cannot be resolved statically.
4. **Check Syntax Validity:** If the source file contains syntax errors, the primary AST parser fails. Check `repopeek.log` for warnings:
   ```text
   WARNING: Failed to parse src/bad_syntax.py with PythonASTParser; fallback regex invoked.
   ```

---

## 3. Graph Explosion and Giant Component Merges (RP-003)

### Symptoms
Blast radius queries for a localized function return hundreds of unrelated nodes spanning backend Python and frontend TypeScript code.

### Root Cause
Unnamespaced common identifiers (such as Python's built-in `next()`, `id`, `open`, or Next.js package imports) collide in global symbol tables, bridging disconnected language ASTs into a single massive cluster.

### Remediation
1. Ensure nodes are addressed by qualified IDs rather than bare symbol names:
   ```bash
   repopeek --impact "repopeek/retrieval/intent.py::IntentClassifier"
   ```
2. Verify that language namespaces are preserved during symbol lookup.

---

## 4. Groq API Rate Limiting (HTTP 429) or Network Hangs

### Symptoms
Semantic enrichment halts or logs repeated HTTP 429 warnings during `repopeek --repo-path .`:
```text
WARNING: Groq API rate limit reached (HTTP 429). Backing off for 4.2 seconds...
```

### Root Cause
Groq Cloud free-tier rate limits (typically 30–60 requests/minute) exceeded when processing large codebases containing hundreds of classes and functions.

### Remediation
1. Switch to offline deterministic enrichment:
   ```bash
   repopeek --repo-path . --offline
   ```
2. Check token consumption beforehand:
   ```bash
   repopeek --repo-path . --dry-run
   ```
3. Set a valid high-tier `GROQ_API_KEY` in your environment.

---

## 5. Corrupted or Stale SQLite Traversal Cache (`cache.db`)

### Symptoms
Queries fail with:
```text
sqlite3.DatabaseError: database disk image is malformed
```
Or queries return stale results after files have been heavily modified on disk.

### Root Cause
Abrupt termination of the process (e.g. killing the process during an uncommitted write transaction) left dangling `-journal` or `-wal` files.

### Remediation
`cache.db` is an ephemeral, derived acceleration index; the authoritative ground truth is always the JSON artifacts (`graph.json`).
1. Delete the corrupted database:
   ```bash
   # Windows PowerShell
   Remove-Item .repopeek/cache.db* -Force
   
   # Linux / macOS
   rm -f .repopeek/cache.db*
   ```
2. Rebuild the cache from `graph.json`:
   ```bash
   python -c "from pathlib import Path; from repopeek.storage.json_store import load_canonical_graph; from repopeek.storage.sqlite_cache import build_sqlite_cache; g = load_canonical_graph(Path('.repopeek')); build_sqlite_cache(g, Path('.repopeek/cache.db')); print('Cache rebuilt successfully')"
   ```

---

## 6. MCP Client Disconnection / Handshake Timeouts

### Symptoms
Cursor or Claude Desktop displays:
```text
MCP Server Disconnected: stdio stream terminated unexpectedly
```

### Root Cause
The stdio MCP transport strictly requires `stdout` to carry valid JSON-RPC 2.0 messages only. If custom code or third-party libraries write standard `print()` statements or unredirected logs to `stdout`, the client JSON parser fails and terminates the connection.

### Remediation
Ensure all logging and diagnostic output is directed exclusively to `sys.stderr` or written to a dedicated log file:
```python
import sys
print("Diagnostic info", file=sys.stderr)
```
Verify that [repopeek/query/mcp_server.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/mcp_server.py) runs cleanly when executed standalone in terminal.
