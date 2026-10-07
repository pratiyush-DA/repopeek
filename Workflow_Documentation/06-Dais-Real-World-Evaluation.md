# Dais real-world evaluation — agent vs RepoPeek+agent

Date: 2026-10-06  
Target: `testing/dais` (`https://github.com/Marketzone-DA/dais.git`)  
Pinned SHA: `345c3d0391d654a6f8adbedee7d51d2ab4ed59a6` (`develop`)  
RepoPeek: no commits; dais reset to the pinned SHA after every patch.

## What was measured

dais is a React (Vite) + Django REST + PostgreSQL synthetic-data platform with Groq metadata generation and Teams webhooks.

This is **not** a second coding-agent model race. Both passes applied the **same gold micro-patches**. Pass A explored with `git grep`. Pass B started from `compile_context` / MCP. That is a real navigation-cost comparison on a real repo; it overstates “task success” if you treat success as independent agent reasoning.

## Index

| Item | Result |
| --- | --- |
| Discovered files | 213 (127 py, 46 js, 9 json, 5 yaml, 1 sql, …) |
| Graph | **4,306 nodes**, **16,239 edges** (under the 400-file / 8k-node abort cap) |
| Offline enrich | **15.6 s**, 0 LLM / 4,077 deterministic / 229 cached |
| Groq enrich | **Aborted** after ~14 min with no progress print (rate-limit / sequential 4k-node story fan-out). MCP/CLI used the offline graph. |
| JSON | 9 files including Postman; **722 `json_config` nodes** (flatten-all-keys). Not an explosion like da-assistant’s 581k nodes. |
| SQL parser | Postgres `init.sql` parsed as Oracle dialect → fallback `command` nodes |

## MCP (all 10 tools) + CLI

Handshake listed all 10 tools. Live engine dispatch:

| Tool | OK | Size | Latency |
| --- | ---: | ---: | ---: |
| `repopeek_resolve` | yes | 12,130 chars | 191 ms |
| `repopeek_lookup` | yes | 3,561 | 3 ms |
| `repopeek_neighbors` | yes | **93,645** | 9 ms |
| `repopeek_impact` | yes | 37,490 (16 affected; includes `ext:py:stdlib:re.sub`) | 15 ms |
| `repopeek_context` | yes | 4,779 (~1.2k tokens, 97% vs raw file) | 275 ms |
| `repopeek_plan` | yes | 2,051 | 22 ms |
| `repopeek_routes` | yes | 37,341 | 46 ms |
| `repopeek_co_changes` | yes | 4,436 | 771 ms |
| `repopeek_data_trace` | yes | 19,390 | 6 ms |
| `repopeek_context_pack` | yes | 762 | 5 ms |

CLI `--lookup generate_metadata_config` and `--routes` matched the same graph.

HTTP bridge on dais: **43 routes**, **18 client calls**, **76 links**. Django `urlpatterns` fired (`app/api/chatbot/urls.py`, generations, users, …). Client `apiFetch` in `app/src/api/client.js` is a **generic wrapper**; many links are path-template noise (`${API_BASE_URL}${path}` → lots of servers).

## Context quality vs gold (`testing/dais/tasks.yaml`)

| Task | Recall | Precision | Context files | Exclusion leak |
| --- | ---: | ---: | ---: | --- |
| DAIS-001 local LLM retries | 100% | 11.1% | 13 | none |
| DAIS-002 recent generations limit | 100% | 20.0% | 3 | none |
| DAIS-003 login error text (JS) | **25%** | **2.9%** | 15 | `app/api/users/views.py` (task forbade Django view) |
| DAIS-004 Teams timeout | 100% | 11.8% | 5 | none |
| DAIS-005 init.sql comment | 100% | 16.7% | 2 | none |
| DAIS-006 login serializer constraint | 100% | 6.1% | 9 | `src/core/generate_synthetic_dataset.py` |
| DAIS-007 preview 10-row comment | 100% | 15.8% | 4 | none |
| DAIS-008 remember-me comment | 75% | 10.3% | 7 | missed `LoginPage.jsx` in files |

**Mean recall 87.5%. Mean precision ~11.8%.** That is far better than the da-assistant 0.57% precision collapse, still an order of magnitude of extra files/symbols vs gold.

## Agent-only vs RepoPeek+agent (gold patch after exploration)

| Task | A files | B context files | A token proxy | B context tokens | A ms | B ms | Edit hit gold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| DAIS-001 | 63 | 11 | 35,413 | 1,179 | 6.0s | 1.0s | both |
| DAIS-002 | 112 | 1 | 67,400 | 1,295 | 6.3s | 0.8s | both |
| DAIS-003 | 52 | 14 | 26,756 | 1,433 | 5.5s | 1.7s | both |
| DAIS-004 | 42 | 4 | 74,000 | 1,426 | 6.7s | 0.8s | both |
| DAIS-005 | 36 | 2 | 6,117 | 955 | 5.2s | 0.8s | both |
| DAIS-006 | 31 | 9 | 26,179 | 1,913 | 5.1s | 1.6s | both |
| DAIS-007 | 14 | 3 | 112,775 | 1,182 | 4.9s | 0.9s | both |
| DAIS-008 | 26 | 7 | 6,655 | 1,516 | 6.4s | 0.9s | both |
| **Mean** | **47** | **6.4** | **~44k** | **~1.4k** | **5.8s** | **1.1s** | **8/8** |

Approximate **86% fewer files** to look at and **~97% smaller token proxy** if the agent trusts the package instead of grepping and reading hits. Wrong-file **edits** were zero because the harness applied gold diffs; **compiled context still leaked excluded files** on DAIS-003 and DAIS-006.

## Product defects (value vs 200% right)

1. **LLM indexing is not production-safe at 4k+ nodes** with the current sequential/pool enrich + Groq 429 behavior. Offline graph is the reliable path today.
2. **`repopeek_neighbors` dumps ~90k chars** — agents should prefer `repopeek_context` / `context_pack`.
3. **Precision ~12%** — gold file is usually in the pack, plus several extras. Exclusion phrases still leak related modules.
4. **Frontend-only tasks** can miss JSX (`DAIS-003`/`008`) or pull the Django view you asked not to touch.
5. **HTTP wrapper linking is too eager** (`apiFetch` → many servers).
6. **JSON flatten** (Postman) inflates `json_config` count; not fatal here.
7. **SQL dialect hardcoded Oracle** on a Postgres repo.
8. **Impact still lists stdlib externals** (`re.sub`) as “affected.” Namespaced, not the old `next` hub, but noisy.

## Judgment: how close to a stable utility?

**Close enough to save agent cost as a navigation layer. Not close enough to be the only context the agent reads.**

Ship as: lookup / resolve / context / routes / impact **with a file-count cap and `--offline` default for large indexes**. Tell agents: do not call `neighbors` unbounded; treat context as a **shortlist**, not a closed world; re-read the gold files.

Do **not** yet call it a stable “compile and stop exploring” product until: Groq enrich is gated by node count, exclusions are hard at file granularity, wrapper HTTP links require a literal path, and neighbor APIs are capped like blast radius.

Frozen synthetic v1 (footnote, not this repo): MRR 0.2267, Recall@5 26%, negative precision 100%.

Raw artifacts (gitignored under `testing/dais/`): `results/mcp_matrix.json`, `results/live_comparison.json`, `results/index.log`, `tasks.yaml`.

## After precision + Groq reliability pass (2026-10-06)

Same pinned dais SHA. Offline graph reindex: **214 files**, **3,871 nodes**, **16,055 edges** (Postman/nested `repopeek/` ignored). Pytest `tests/`: **193 passed**, 1 skipped (live Groq 429).

MCP payload caps (same lookup node as before):

| Tool | Chars |
| --- | ---: |
| `repopeek_neighbors` | **9,190** (was 93,645; under 15k) |
| `repopeek_routes` | 15,649 |
| `repopeek_data_trace` | 11,314 |
| `repopeek_impact` | 20,029 |
| `repopeek_context` | 4,364 (~1.1k tokens, 92% reduction) |

Context vs gold (file cap 4, span snippets, NL + yaml exclusions):

| Task | Recall | Precision | Context files | Exclusion leak |
| --- | ---: | ---: | ---: | --- |
| DAIS-001 | 100% | 16.7% | 5 | none |
| DAIS-002 | 100% | 27.3% | 3 | none |
| DAIS-003 | **50%** | 5.6% | 3 | **none** (`views.py` gone; `AuthContext.jsx` ranked) |
| DAIS-004 | 100% | 20.0% | 4 | none |
| DAIS-005 | 100% | 16.7% | 2 | none |
| DAIS-006 | 100% | 9.1% | 4 | **none** (`generate_synthetic_dataset.py` gone) |
| DAIS-007 | 100% | 30.0% | 4 | none |
| DAIS-008 | 75% | 15.0% | 4 | none (still misses `LoginPage.jsx` in files) |

**Mean recall ~90.6%. Mean precision ~17.5%** (aim was ≥40% on this 8-task file+symbol metric; not met). Mean files in pack **~3.6** (was 6.4 / 15). Exclusion leaks **0/8**.

Groq: `GROQ_API_KEY` plus optional `_2`/`_3`; default concurrency 2; LLM top-K 200; 429 cools one key then template fallback. Live completion skipped on 429. Tiny top-K smoke (12 functions, `REPOPEEK_LLM_MAX_NODES=3`) **finished in ~7s** with a heartbeat (`0 LLM / 12 deterministic`). Only **one** key was configured in local `.env` at re-measure time.

Honest ceiling unchanged: agents get a shortlist + spans, not a closed world. Do not put API keys in git.

## Groq top-K re-index + agent vs RepoPeek+agent (2026-10-06)

Local `.env` had **three** Groq keys (`GROQ_API_KEY` plus `_2` and `_3`). Values are not recorded here. Index command: unbuffered `python -u -m repopeek --repo-path testing/dais --output-dir testing/dais/repopeek` with `REPOPEEK_LLM_MAX_NODES=200` and `REPOPEEK_LLM_CONCURRENCY=2` (no `--offline`). Pinned SHA still `345c3d0391d654a6f8adbedee7d51d2ab4ed59a6`. Dais working tree clean after live patches.

### Index

| Item | Result |
| --- | --- |
| Files | 215 (graph 3,871 nodes / 16,057 edges; under 400 / 8k abort) |
| Wall time | **~141 s** (graph + enrich + persist) |
| Stories | 3,871 total: **98 LLM**, 3,698 deterministic, 75 cached |
| Heartbeats | Printed every 25 nodes; run finished (did not hang) |
| vs offline | Same graph size; LLM overlay did **not** change retrieval topology |

`generate_metadata_config` still has a **deterministic** story (`complexity` 30) — Groq did not replace that hotspot. SQL `CREATE EXTENSION` / `ALTER DEFAULT PRIVILEGES` still fall back as `Command`.

### MCP (10/10) + CLI

| Tool | OK | Chars | ms |
| --- | ---: | ---: | ---: |
| `repopeek_resolve` | yes | 11,687 | 721 |
| `repopeek_lookup` | yes | 3,561 | 16 |
| `repopeek_neighbors` | yes | **9,190** | 1 |
| `repopeek_impact` | yes | 20,029 | 57 |
| `repopeek_context` | yes | 4,364 | 729 |
| `repopeek_plan` | yes | 2,050 | 69 |
| `repopeek_routes` | yes | 15,649 | 156 |
| `repopeek_co_changes` | yes | 4,436 | 1,612 |
| `repopeek_data_trace` | yes | 10,237 | 13 |
| `repopeek_context_pack` | yes | 762 | 16 |

CLI `--lookup generate_metadata_config` and `--routes` matched the graph (**43 routes**, **8 calls**, **15 links**).

### Context vs gold (same 8 tasks)

| Task | Recall | Precision | Files | Leak |
| --- | ---: | ---: | ---: | --- |
| DAIS-001 | 100% | 18.8% | 5 | none |
| DAIS-002 | 100% | 27.3% | 3 | none |
| DAIS-003 | 50% | 5.6% | 3 | none |
| DAIS-004 | 100% | 20.0% | 4 | none |
| DAIS-005 | 100% | 16.7% | 2 | none |
| DAIS-006 | 100% | 9.1% | 4 | none |
| DAIS-007 | 100% | 30.0% | 4 | none |
| DAIS-008 | 75% | 15.0% | 4 | none |

**Mean recall ~90.6%. Mean precision ~17.8%.** Same leaks-zero and JSX miss as the offline precision pass. Groq stories did not lift DAIS-003/008 ranking.

### Agent-only vs RepoPeek+agent (gold micro-patches)

Same harness as before: Pass A `git grep` + gold edit; Pass B `compile_context` + the **same** gold edit. Not two independent coding agents.

| Task | A files | B files | A token proxy | B tokens | A ms | B ms | Gold hit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| DAIS-001 | 63 | 4 | 35,413 | 1,083 | 8.7s | 2.0s | both |
| DAIS-002 | 112 | 3 | 67,400 | 1,202 | 9.1s | 1.8s | both |
| DAIS-003 | 52 | 3 | 26,756 | 1,301 | 6.8s | 3.4s | both |
| DAIS-004 | 42 | 4 | 74,000 | 1,294 | 10.7s | 1.7s | both |
| DAIS-005 | 36 | 2 | 6,117 | 955 | 7.9s | 1.4s | both |
| DAIS-006 | 31 | 4 | 26,179 | 1,753 | 8.1s | 1.9s | both |
| DAIS-007 | 14 | 4 | 112,775 | 852 | 8.6s | 1.7s | both |
| DAIS-008 | 26 | 4 | 6,655 | 1,413 | 7.7s | 1.1s | both |
| **Mean** | **47** | **3.5** | **~44k** | **~1.2k** | **8.4s** | **1.9s** | **8/8** |

RepoPeek cut exploration to **~7% of grep files** and **~3% of the token proxy**. Edit success is **not** evidence of independent reasoning: both passes applied the same gold diffs. Wrong-file edits were zero for that reason. Context still omits `LoginPage.jsx` (DAIS-008) and is weak on DAIS-003 symbol recall.

### Issues found this run

1. **LLM overlay is thin in practice:** 98/3871 stories (~2.5%) from Groq; many hotspots (including `generate_metadata_config`) stayed templates. Retrieval/precision vs gold is essentially the offline pack.
2. **Heartbeat counters lag** during the first methods thread-pool batch (prints `0 LLM` until that batch joins). The run still finished.
3. **Precision still ~18%** (file+symbol metric). Agents still must open gold files; pack is a shortlist.
4. **Frontend miss:** DAIS-003 recall 50%; DAIS-008 still misses `LoginPage.jsx`.
5. **HTTP false links:** `downloadUrl` / `wrapper` still match `:param` swagger/upload routes; 15 links, some junk.
6. **SQL dialect:** Postgres `init.sql` still emits Command fallbacks for `CREATE EXTENSION` / `ALTER DEFAULT PRIVILEGES`.
7. **Impact payload** (~20k chars) still larger than neighbors; `django_or_route_hint` in the matrix stayed false despite 43 Django routes (harness preview check, not missing routes).
8. **Keys in chat remain compromised** if they were pasted earlier — rotate in Groq console. Do not commit `.env`.

### Judgment

With a 3-key pool, Groq **indexing is now usable** (~2.4 min, no hang). It does **not** make RepoPeek the closed-world source of truth. Ship as: offline graph first, optional Groq overlay, `resolve`/`lookup`/`context` as a **shortlist + spans**. Agent-only grep is much more expensive; RepoPeek+agent is cheaper **if the agent trusts the pack and still opens the 2–4 listed files**.

Raw artifacts: `testing/dais/results/index_groq.log`, `mcp_matrix.json`, `live_comparison.json`.

## Trusted-map pass (scratch offline reindex, 2026-10-06)

Deleted `testing/dais/repopeek/` and reindexed **offline** (`--offline`, ~20s). Files **216**, graph **3,872 nodes / 16,051 edges**, **0 LLM / 3,797 deterministic / 75 cached**. Pinned SHA unchanged; dais tree clean.

Gates vs plan:

| Gate | Result |
| --- | --- |
| Mean **file recall** ≥ 0.875 | **1.00** (gold file in pack on all 8; DAIS-008 now includes `LoginPage.jsx` + `views.py`) |
| Zero exclusion leaks | **0/8** |
| Mean **file precision** ≥ 0.40 | **0.33** (not met; 1 gold file in a 3–4 file cap) |
| Neighbors &lt; 15k | **9,190** |
| Identifier HTTP (`downloadUrl`/`wrapper`) | skipped; routes payload **11,321** (was 15.6k) |
| Impact cap | **3,589** chars (was ~20k) |
| Offline index | **~20 s** |

Context vs gold:

| Task | File recall | File prec | Mixed recall | Files | Leak |
| --- | ---: | ---: | ---: | ---: | --- |
| DAIS-001 | 100% | 33% | 100% | 3 | none |
| DAIS-002 | 100% | 33% | 100% | 3 | none |
| DAIS-003 | 100% | 25% | 50% (symbol) | 4 | none |
| DAIS-004 | 100% | 25% | 100% | 4 | none |
| DAIS-005 | 100% | 50% | 100% | 2 | none |
| DAIS-006 | 100% | 25% | 100% | 4 | none |
| DAIS-007 | 100% | 25% | 100% | 4 | none |
| DAIS-008 | 100% | 50% | 75% (symbol) | 4 | none |

Agent-only vs RepoPeek+agent (same gold patches): mean **47 → 3.5 files**, token proxy **~44k → ~1.9k** (40-line spans; a few tasks exceed 2k). Gold hit 8/8 both sides. Packs now emit `coverage: full|partial`.

Still not a closed world: extra files in the cap, weak DAIS-003 symbols, some snippet budgets over 2k. Primary map: **open the listed files; skip repo-wide grep.**


## Precision + symbol + edge-trust pass (scratch offline reindex, 2026-10-06)

Same pinned dais SHA. Deleted `testing/dais/repopeek/` and reindexed **offline**. Graph **4,020 nodes / 16,898 edges** (was 3,872 / 16,051 — the +148 nodes are JS hook-wrapped callbacks and SCREAMING_SNAKE module constants now emitted; still far under the 400-file / 8k-node abort cap). Pytest `tests/`: **204 passed** (6 new regression tests).

### What changed (code)

- **Context compiler** (`repopeek/context/compiler.py`): file-grain ranking now scores each file **once** (entrypoint rank + blast membership) and keeps the top file plus only those within a **relative band** (`>= 0.5 * top`), instead of padding to 4 unconditionally. `frontend_intent` requires an explicit client-side signal (a bare "login" no longer fires it, which had pulled JSX into backend tasks). A post-threshold **frontend recall backstop** adds exactly one best-matching client file when a frontend task kept none (keeps cross-stack gold like `LoginPage.jsx`). New **token-budget enforcement** sheds surplus neighbor snippets → indirect → extra direct cards while keeping the primary entrypoint and one snippet per shortlisted file. Risk level is computed from the full pre-trim blast radius so trimming never softens a schema/HIGH assessment.
- **HTTP bridge** (`repopeek/bridges/http.py`): `normalize_route_path` strips a leading `${VAR}` while **preserving the literal path** (`${API_BASE_URL}auth/login` → `/auth/login`, previously `/login`). Matching still requires ≥1 shared literal segment and the most-specific server; result is strictly more specific, so no new false matches.
- **SQL parser** (`repopeek/parsers/sql.py`): `exp.Create` is dispatched by `kind`. Only `TABLE` becomes `sql_table`; `FUNCTION`/`VIEW`/`EXTENSION`/etc. route to the command handler. `CREATE OR REPLACE FUNCTION fix_timezone_setting()` is now `function.fix_timezone_setting` (a function), not a false schema table.
- **TS/JS parser** (`repopeek/parsers/typescript.py`): emits hook/HOC-wrapped arrows (`useCallback`/`useMemo`/`memo`/`forwardRef`) and SCREAMING_SNAKE module constants. `login`, `API_BASE_URL`, `REMEMBER_ME_DAYS` are now nodes.

### Gates vs plan

| Gate | Before (trusted-map) | After |
| --- | --- | --- |
| Mean **file precision** ≥ 0.40 | 0.33 | **0.79** |
| Mean **file recall** ≥ 0.875 | 1.00 | **1.00** |
| Zero exclusion leaks | 0/8 | **0/8** |
| `repopeek_neighbors` < 15k | 9,190 | **9,190** |
| `repopeek_impact` cap | 3,589 | **3,589** |
| Pack tokens ~1–2k | some > 2k | **all ≤ 1,601** |
| SQL/HTTP edges don't lie | function mislabeled table | **function labeled function; 3 HTTP links, 0 junk** |

### Context vs gold (same 8 tasks)

| Task | File recall | File prec | Mixed recall | Files | Tokens | Leak |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| DAIS-001 | 100% | 50% | 100% | 2 | 1,333 | none |
| DAIS-002 | 100% | 100% | 100% | 1 | 1,060 | none |
| DAIS-003 | 100% | 100% | 75% (sym `login`) | 1 | 1,050 | none |
| DAIS-004 | 100% | 33% | 100% | 3 | 1,601 | none |
| DAIS-005 | 100% | 100% | 100% | 1 | 671 | none |
| DAIS-006 | 100% | 100% | 100% | 1 | 1,296 | none |
| DAIS-007 | 100% | 100% | 75% (sym) | 1 | 1,469 | none |
| DAIS-008 | 100% | 50% | 100% | 2 | 1,347 | none |

**Mean file precision ~0.79. Mean file recall 1.00. Mean mixed recall ~0.94.** Exclusion leaks 0/8.

### MCP (10/10) payloads (same lookup node)

| Tool | Chars |
| --- | ---: |
| `repopeek_resolve` | 11,742 |
| `repopeek_lookup` | 4,720 |
| `repopeek_neighbors` | 9,190 |
| `repopeek_impact` | 3,589 |
| `repopeek_context` | 4,523 (~1.1k tokens) |
| `repopeek_routes` | 12,951 |
| `repopeek_data_trace` | 11,314 |
| `repopeek_context_pack` | 762 |

### Agent-only vs RepoPeek+agent (same gold micro-patches)

Pass A `git grep` + gold edit; Pass B `compile_context` + the **same** gold edit (not two independent agents). Gold hit **8/8 both sides**. Mean grep **47 files → 1.5 context files**; token proxy **~44k → ~1.2k** (every pack < 2k now, vs a few > 2k in the trusted-map pass).

### Honest ceiling / remaining

- Still a **shortlist + spans**, not a closed world: DAIS-004 keeps 3 files (gold `teams_utils.py` ranks #2 behind `generate_preview`), so file precision there is 33%.
- Symbol recall improved where emission was the blocker (DAIS-003 `login` 0 → in pack) but is not complete: DAIS-003 `API_BASE_URL` exists as a node yet is not surfaced in the 1-file compact pack, and DAIS-007 `generate_preview` dropped because its file was trimmed for precision (file recall still 100%; the gold edit site is in the pack). These are ranking/compaction limits, not emission gaps.
- Groq overlay unchanged and still optional; `--offline` is the measured path here.
- Primary-map guidance unchanged: **open the listed files; skip repo-wide grep.**
