# Production-readiness improvement plan (post-dcnc)

Date: 2026-10-06. Derived from `08-DCNC-Real-World-Evaluation.md`. Scope follows the Ponytail
Decision Ladder (YAGNI → existing code → stdlib → existing deps → smallest correct fix). Each
item lists the root cause, the chosen approach, scope, and acceptance criteria.

## P1 — correctness blockers (fix now)

### P1a. Anchor embedded SQL DDL in Python
- **Root cause:** `repopeek/parsers/python.py` detects an embedded `CREATE TABLE` string but
  emits a generic `sql_query` node named `query_L{line}` and routes the created table through
  `find_all(exp.Table)` as a **read**, which the resolver turns into
  `ext:sql:unresolved:<table>` (no file/span). A schema task on such a table cannot resolve to
  the hosting `.py` file (dcnc DCNC-005: file recall 0).
- **Approach (best fit, reuses existing deps):** in the embedded-SQL branch, dispatch
  `exp.Create` by `kind` exactly like `repopeek/parsers/sql.py`: `TABLE` → a file-anchored
  `sql_table` node `sql:<pyfile>::table.<name>` (name-searchable, `facts.writes=[name]`);
  `FUNCTION` → `function.<name>`. The created object is **not** emitted as an unresolved read.
- **Scope:** `repopeek/parsers/python.py` embedded-SQL block only. No new deps.
- **Acceptance:** DCNC-005 file recall → 1.0; `pattern_cache` resolves to `db_manager.py`;
  no `ext:sql:unresolved:pattern_cache` for a table defined in the file.

### P1b. Data-layer intent disambiguation
- **Root cause:** the term "pattern_cache" matched the eponymous module
  `pattern_cache.py` more strongly than the schema host `db_manager.py`.
- **Approach:** in `repopeek/context/compiler.py` file scoring, when the task carries DDL/data
  signals ("schema", "create table", "column", "database", "migration"), add a modest boost to
  files that host SQL/DDL (`.sql`, or `.py` files containing `sql_table`/embedded-SQL nodes).
- **Scope:** `compiler.py` `_score_file` + a cheap task-signal check. **Acceptance:** DCNC-005
  resolves `db_manager.py` as the top file without regressing the other 7 tasks.

## P2 — quality

### P2a. Bounded Python symbol-grain
- **Root cause:** parameter defaults (`max_retries`) and module-level dicts/constants are not
  nodes, so param-level gold symbols are only partially retrievable (DCNC-001 mixed 0.75).
- **Approach:** mirror the TS SCREAMING_SNAKE work — emit `variable` nodes for module-level
  SCREAMING_SNAKE constants and module-level dict/list assignments (e.g. `STRATEGY_MAP`) in
  `repopeek/parsers/python.py`. Bounded to all-caps names + top-level assignments to avoid
  node inflation. **Acceptance:** `STRATEGY_MAP` retrievable; no large node-count regression.

### P2b. Honest empty-tool responses
- **Root cause:** `co_changes` (squashed history) and `routes` (non-web repo) return empty
  arrays with no explanation; agents may read it as a failure.
- **Approach:** add an explicit `note` field ("no git co-change history found" / "no HTTP
  routes detected" / "no data entity matched") in `repopeek/query/engine.py`.

## P3 — hardening

### P3a. Systemic MCP payload budget
- **Root cause:** impact ballooned to 336k on a hub node (fixed in the dcnc pass). The budget
  should be structural, not per-tool.
- **Approach:** a small shared helper that caps any oversized JSON tool payload; apply to the
  large tools (resolve, data_trace, routes). The impact cap already lives in
  `blast_radius.py`. **Acceptance:** every MCP tool ≤ ~15k on any graph shape.

### P3b. Index transparency
- **Root cause:** dcnc skipped ~17k `venv` files silently.
- **Approach:** print an ignored-vs-indexed summary at index time (`repopeek/cli.py`).

## Out of scope / later
- Cross-resolution of embedded-SQL DML references to embedded-table definitions (resolver work).
- A full managed service, vector DB, or new-language parsers (unchanged scope guardrails).

## Verification
`$env:PYTHONPATH="."; .venv\Scripts\python -m pytest tests` green, re-index dcnc offline, re-run
`run_mcp_matrix.py` + `run_live_compare.py`, confirm DCNC-005 fixed and all gates hold, then
vault DoD (`validate.py` zero errors) and commit.


## Status (2026-10-06) — implemented

| Item | Status | Notes |
| --- | --- | --- |
| P1a Embedded SQL DDL anchoring | **Done** | `python.py`: `CREATE TABLE`/`FUNCTION` in strings → `table.<name>`/`function.<name>` file-anchored nodes; created table no longer an unresolved read. Test added. |
| P1b Data-layer intent disambiguation | **Done** | `compiler.py`: `data_intent` boost + a data/schema recall backstop that adds every file defining a task-matched table. |
| P2a Python symbol-grain | **Already covered** | `_process_assignment` already emits module/class `variable` nodes (`STRATEGY_MAP`). Parameter defaults intentionally not emitted (inflation). |
| P2b Honest empty-tool responses | **Done** | `engine.http_routes`/`data_trace` add a `note` when empty; MCP `co_changes` note on empty. |
| P3a Systemic MCP payload budget | **Done** | MCP boundary guard (≤15k, valid JSON) over all tools; per-tool caps + the impact cap keep normal results small. |
| P3b Index transparency | **Done** | `cli.py` prints "Ignored (not indexed): …". |

Result on dcnc: file recall 0.875 → **1.000**, file precision 0.875 → **0.938**, DCNC-005 recall
0 → **1.0**, live-compare gold reachable 7/8 → **8/8**. Full suite **207 passed**. See
`08-DCNC-Real-World-Evaluation.md` → *Post-improvement results*.

Deferred (unchanged scope): cross-resolution of embedded-SQL DML refs to embedded-table defs;
per-parameter symbol nodes.
