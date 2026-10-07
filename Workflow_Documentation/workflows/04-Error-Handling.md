# Error Handling & Failure Recovery

This document details failure conditions, exception hierarchies, fallback mechanisms, swallowed errors, and operational recovery paths across all RepoPeek subsystems.

---

## 1. Subsystem Error Matrix

| Subsystem | Failure Condition | Raised Exception | Handling Mechanism | Fallback / Final Behavior |
|---|---|---|---|---|
| **Discovery** | File permission denied or unreadable | `OSError`, `PermissionError` | Caught in `try...except` | File skipped; excluded from discovered file list. |
| **Discovery** | Non-existent repository path | `ValueError` | Caught in `cli.main()` | Prints error to `stderr`, exits with status 1. |
| **Python Parser** | Invalid Python syntax in source file | `SyntaxError` | Caught in `parse_source()` | Activates `_parse_fallback()` (regex parser). Extracts functions/classes; marks story confidence as `"unresolved"`. |
| **SQL Parser** | Unrecognized SQL dialect or syntax error | `sqlglot.errors.ParseError` | Caught in dialect loop | Attempts Oracle -> Postgres -> ANSI -> Regex fallback (`_fallback_extract`). |
| **Shell Parser** | Malformed quotation or syntax in shell | `shlex.ValueError` | Caught in `parse_source()` | Appends warning to `errors` list; splits line naively by whitespace. |
| **Config Parser** | Corrupted or malformed JSON | `json.JSONDecodeError` | Caught in `parse_source()` | Returns `ParseResult` with file node and error string; does not crash pipeline. |
| **Config Parser** | Corrupted or malformed YAML | `yaml.YAMLError` | Caught in `parse_source()` | Returns `ParseResult` with file node and error string; does not crash pipeline. |
| **Symbol Resolver** | Target symbol or import not found | None (silent) | Returns `None` | Sets edge confidence to `Confidence.EXTERNAL` or `Confidence.UNRESOLVED`. |
| **HTTP Bridge** | Malformed route decorator or regex miss | `Exception` | Caught in `GraphBuilder` | Swallowed via `except Exception: pass`; graph built without HTTP edge. |
| **Temporal Miner** | Missing `.git` directory or git command failure | `subprocess.SubprocessError` | Caught in `mine_commits()` | Returns empty commit list `[]`; graph built without temporal edges. |
| **LLM Provider** | Invalid API key or missing `GROQ_API_KEY` | `LLMAuthenticationError` | Caught in `HierarchicalStoryGenerator` | Records fallback in `CostGovernor`; generates deterministic AST template. |
| **LLM Provider** | HTTP 429 Rate Limit from Groq API | `LLMRateLimitError` | Exponential backoff retry | Retries up to 3 times ($t \cdot 2^i$). If exhausted, falls back to deterministic template. |
| **LLM Provider** | Network timeout or HTTP 5xx from Groq | `LLMProviderError` | Exponential backoff retry | Retries up to 3 times. If exhausted, falls back to deterministic template. |
| **Fact Verifier** | Generated story references hallucinated tables | `VerificationResult.is_valid = False` | Checked in `summarizer` | Rejects LLM story; replaces with `DeterministicStoryBuilder` narrative. |
| **Fact Verifier** | Generated story claims calls when `calls == 0` | `VerificationResult.is_valid = False` | Checked in `summarizer` | Rejects LLM story; replaces with `DeterministicStoryBuilder` narrative. |
| **Storage** | Target directory locked by another process (Windows) | `PermissionError`, `OSError` | Caught in `json_store` | Staging directory cleanup attempted; logs warning. |
| **Query Engine** | Queried node ID or symbol does not exist | None | Returns `None` / `BlastRadiusReport(found=False)` | CLI prints error message and exits with status 1. |
| **MCP Server** | Unrecognized tool name requested | JSON-RPC error | Handled in `_execute_tool` | Returns JSON-RPC error code `-32601` ("Method not found"). |
| **Watch Daemon** | File deleted during active watch loop | `FileNotFoundError` | Caught in `scan_changes()` | Deletes node from in-memory graph; drops affected edges. |

---

## 2. Deep Dive: Resilient Parser Fallbacks

### Python Syntax Error Fallback
When a Python file has invalid syntax (e.g. broken edits, merge conflict markers, incomplete templates), standard `ast.parse()` raises `SyntaxError`. In [`repopeek/parsers/python.py:_parse_fallback`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/python.py#L63):

```python
try:
    tree = ast.parse(source, filename=norm_path)
    return self._parse_ast(...)
except SyntaxError as exc:
    return self._parse_fallback(source, source_lines, norm_path, syntax_error=exc)
```

The fallback parser uses regexes (`FALLBACK_FUNC_RE`, `FALLBACK_CLASS_RE`, `FALLBACK_IMPORT_RE`) to salvage:
- Class definitions and base classes.
- Function and method definitions and parameter names.
- Explicit import statements.
- Tags file and symbol nodes with `confidence="unresolved"`.
- Adds the syntax error message to `ParseResult.errors`.

### SQL Multi-Dialect Fallback Loop
In [`repopeek/parsers/sql.py:parse_source`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/sql.py#L68):

```python
dialects_to_try = [active_dialect]
if active_dialect != "postgres":
    dialects_to_try.append("postgres")
if "" not in dialects_to_try:
    dialects_to_try.append("")  # Generic ANSI
```

If all dialects fail to parse via `sqlglot`, `self._fallback_extract()` scans line-by-line for `CREATE TABLE <name>`, `SELECT ... FROM <name>`, and `INSERT INTO <name>` using regexes, ensuring tables and query cards still enter the graph.

---

## 3. Deep Dive: LLM Resilience and Fact Verification

### Exponential Backoff and Retries
In [`repopeek/llm/groq.py:complete`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/llm/groq.py#L120):
- Intercepts `urllib.error.HTTPError`.
- For HTTP 429 (Rate Limit) and HTTP 500/502/503/504 (Server Errors):
  - Retries up to `max_retries` (default 3).
  - Sleeps for $2^{\text{attempt}} \times 0.5$ seconds with jitter.
- For HTTP 401/403:
  - Raises non-retryable `LLMAuthenticationError` immediately.
- If all retries fail:
  - Raises `LLMRateLimitError` or `LLMProviderError`.

### Anti-Hallucination Guardrail (`FactVerifier`)
In [`repopeek/enrichment/verifier.py:verify`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/enrichment/verifier.py#L23):
1. **Length Check:** If words > 60, fails verification.
2. **Raw Code Dump Check:** If candidate text contains ` ``` `, `def `, or `class `, fails verification.
3. **Table Entity Grounding:** Matches any referenced table words against `node.facts.reads` and `node.facts.writes`. If an unrecorded table name appears, fails verification.
4. **Call Count Grounding:** If `node.facts.calls == 0` and the text claims external calls, fails verification.
5. **Fallback:** If `verify()` returns `is_valid=False`, `HierarchicalStoryGenerator` discards the text and calls `DeterministicStoryBuilder.build_story(node)`.

---

## 4. Swallowed Exceptions and Architectural Risks

The following locations in the codebase deliberately catch and suppress exceptions (`except Exception: pass`). These represent intentional trade-offs for resilience, but require engineering awareness:

### 1. HTTP Bridge Resolution in `GraphBuilder`
```python
# repopeek/graph/builder.py lines 91-92
except Exception:
    pass
```
- **Rationale:** Prevents a parsing anomaly or missing route pattern from blocking canonical graph assembly.
- **Risk:** If a bug exists in `HttpBoundaryBridge`, cross-language `INVOKES` edges fail silently without warnings.

### 2. Temporal Miner Execution in `GraphBuilder`
```python
# repopeek/graph/builder.py lines 133-134
except Exception:
    pass
```
- **Rationale:** Ensures RepoPeek runs cleanly in environments without `git` installed or in git archives without `.git`.
- **Risk:** Unexpected git log parsing errors will silently omit `CO_CHANGED_WITH` edges.

### 3. FTS5 Incremental Index Synchronization in `SQLiteCache`
```python
# repopeek/storage/sqlite_cache.py lines 380-381
except Exception:
    pass  # FTS5 sync is best-effort for incremental updates
```
- **Rationale:** Guarantees <50ms file update performance without failing if FTS5 table state is locked.
- **Risk:** If an FTS5 update fails during an incremental watch event, full-text search results for that file could remain slightly stale until the next full rebuild.
