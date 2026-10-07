# DCNC real-world evaluation — final pre-production test

Date: 2026-10-06
Target: `testing/dcnc` (`https://github.com/pratiyush-DA/dcnc.git`, branch `develop`)
Pinned SHA: `ba62a4904bbc8efd12e9c9746a94ca65e107d753`
RepoPeek: offline index, no commits; dcnc working tree untouched (no gold patches applied — this pass measures navigation cost + reachability).

## Why this repo

dcnc is a **pure-Python data anomaly detection + correction pipeline** (clustering, correction, detection, type engines, fingerprinting, LLM reshuffling, workflows, a unified SQLite cache, and a CLI). It is deliberately a very different profile from dais (React + Django + SQL): no web layer, no cross-language HTTP, embedded SQL DDL inside Python strings, and a committed `venv/` of ~17k files. A good stress test of generalization on an unseen codebase with zero tuning.

## Index

| Item | Result |
| --- | --- |
| Working-tree files | 17,341 (incl. committed `venv/`, `output/`, `testing_data/`) |
| Indexed source | **87 files** (`venv`/`output`/`testing_data`/`__pycache__`/`site-packages` ignored by default rules — no abort, no explosion) |
| Graph | **2,973 nodes / 10,455 edges** (under the 400-file / 8k-node abort cap) |
| Enrich | offline, **0 LLM / 2,959 deterministic / 14 cached** |
| Node kinds | external_symbol 1,100 · yaml_config 756 · method 531 · variable 334 · class 94 · file 87 · sql_query 41 · function 30 |

## MCP (10/10 tools respond)

| Tool | Chars | Note |
| --- | ---: | --- |
| `repopeek_resolve` | 13,154 | |
| `repopeek_lookup` | 2,272 | |
| `repopeek_neighbors` | 6,388 | < 15k |
| `repopeek_impact` | **13,032** | was **335,969** before the hub-payload cap this pass |
| `repopeek_context` | 5,703 | ~1.1k tokens |
| `repopeek_plan` | 1,898 | |
| `repopeek_routes` | 109 | no web layer (correctly empty) |
| `repopeek_co_changes` | 2 | squashed git history → no co-change signal |
| `repopeek_data_trace` | 2,390 | |
| `repopeek_context_pack` | 798 | |

## Context vs gold (8 authored tasks — `testing/dcnc/tasks.yaml`)

| Task | Category | File recall | File prec | Mixed recall | Files | Tokens | Leak |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| DCNC-001 LLM retry budget | local_behavior | 100% | 100% | 75% | 1 | 1,454 | none |
| DCNC-002 LLM timeout (excl. llm_client) | constrained_config | 100% | 100% | 100% | 1 | 1,347 | none |
| DCNC-003 phone max digits | engine_logic | 100% | 100% | 100% | 1 | 1,445 | none |
| DCNC-004 alias threshold | data_layer | 100% | 100% | 100% | 1 | 1,250 | none |
| DCNC-005 pattern_cache schema comment | data_schema | **0%** | **0%** | 25% | 1 | 1,459 | none |
| DCNC-006 age semantic bound | ml_routing | 100% | 100% | 100% | 1 | 1,454 | none |
| DCNC-007 detection sample (excl. detector) | cross_module_constrained | 100% | 100% | 100% | 1 | 1,327 | none |
| DCNC-008 CLI output dir | cli | 100% | 100% | 100% | 1 | 1,081 | none |

**Mean file recall 0.875 · file precision 0.875 · mixed recall 0.875 · exclusion leaks 0/8 · all packs 1,081–1,459 tokens.**

## Agent-only (git grep) vs RepoPeek+agent

Pass A greps the source tree for the task's salient identifiers and opens the matches; Pass B uses `compile_context`. Navigation cost + gold-file reachability (not two independent agents).

| | Agent-only (grep) | RepoPeek+agent |
| --- | ---: | ---: |
| Mean files to open | **28.9** | **1.0** |
| Mean token proxy | **~65,300** | **~1,350** |
| Gold file reachable | 8/8 (buried among ~29 files) | 7/8 |

RepoPeek cuts files to open by **~97%** and the token proxy by **~98%**, surfacing the gold file as the single pack file on 7/8 tasks.

## Strongholds

1. **Cold-start precision + recall.** 0.875 / 0.875 on a never-seen pure-Python repo with zero tuning; 7/8 tasks return the exact single gold file at 100% precision.
2. **Tight, in-budget packs.** Mean 1.0 file / ~1,350 tokens; every pack within the ~1–2k budget — the token-budget enforcement holds on a new profile.
3. **Exclusions honored.** DCNC-002 (`llm_client.py`) and DCNC-007 (`workflow_detector.py`) negative constraints produced zero leaks.
4. **Profile generalization + scale safety.** Handled a Python-only pipeline (vs dais' polyglot web stack) unchanged, and correctly ignored a committed 17k-file `venv/` — no explosion, no abort.
5. **All 10 MCP tools respond and (after this pass) all payloads are bounded.**
6. **Deterministic + offline.** 0 LLM calls, fast; identical inputs → identical graph.

## Weaknesses (root-caused)

1. **Impact payload exploded on hub nodes (FIXED this pass).** `impact(LLMClient)` returned **335,969 chars** because `BlastRadiusReport.to_dict()` serialized the full per-hop `paths` evidence (668 hops) with node-count caps but no size cap. Latent since the dais work — only a hub-heavy graph exposed it. Fixed: compact node serialization (no `paths`, truncated story) + a hard char-budget guard → **13,032 chars**. Regression test added.
2. **Embedded SQL DDL is not file-anchored.** The `CREATE TABLE pattern_cache` lives inside a Python string in `db_manager._init_database`, but it is only captured as `ext:sql:unresolved:pattern_cache` (no file/span). So DCNC-005's "document the pattern_cache schema" task could not resolve to `db_manager.py`.
3. **Retrieval name-collision ambiguity.** The term "pattern_cache" matched an eponymous module `backend/core/llm/pattern_cache.py` far more strongly than the embedded table, so the pack pointed at the module, not the schema host. Combined with (2), this is why DCNC-005 scored 0 on file recall.
4. **Symbol-grain is partial for Python param defaults / module dicts.** DCNC-001 `max_retries` (a `__init__` parameter default) is not its own node (file recall 100%, symbol recall 50% → mixed 0.75). Module-level `STRATEGY_MAP` surfaced only via its accessor `get_clusterer`.
5. **Silent empties on tool mismatch.** `co_changes` (squashed history) and `routes` (no web layer) return near-empty payloads with no explanatory signal, which can confuse an agent into thinking the tool failed.

## Improvement plan (prioritized)

**P0 — done this pass**
- Cap the impact payload (compact nodes + hard char budget). Shipped + tested.

**P1 — before production**
- **Anchor embedded SQL DDL.** In the Python parser's embedded-SQL path, emit a file-anchored `sql_table`/`sql_query` node (span = the string literal in the `.py` file) instead of only an `ext:…:unresolved` node. Reuse the existing `repopeek/parsers/sql.py` extraction on the embedded string. Fixes weakness 2 and makes "schema defined in Python" first-class.
- **Disambiguate data-layer intent.** When a task carries schema/DDL signals ("CREATE TABLE", "schema", "column", "database"), boost files that host DDL (`*.sql`, embedded-DDL `.py`) over eponymous modules in `compiler.py` file scoring. Fixes weakness 3.

**P2 — quality**
- **Python symbol-grain parity with TS.** Emit searchable nodes/facts for notable module-level constants, dataclass field defaults, and top-level dicts (mirroring the TS SCREAMING_SNAKE const work), so param-level gold symbols (`max_retries`, `timeout`) are retrievable. Keep it bounded (named/typed defaults only) to avoid node inflation.
- **Honest empty-tool responses.** Have `co_changes`/`routes`/`data_trace` return an explicit "no git history / no web routes / no data entity found" marker instead of an empty array.

**P3 — hardening + scale**
- **Systemic payload budget.** Factor a shared `<15k` budget helper and apply it to every MCP tool (resolve, data_trace, routes), so no tool can exceed the bar on any graph shape — impact was the last known offender; make it structural.
- **Index transparency.** Print an ignored-vs-indexed file summary (dcnc skipped ~17k `venv` files) so users can confirm scope at a glance.
- **Eval breadth.** Add more cross-file / cross-layer gold tasks per repo and a lightweight task-authoring aid.

## Judgment

On a cold, unseen pure-Python repository with no tuning, RepoPeek delivered **0.875 file precision, 0.875 file recall, zero exclusion leaks, ~1 file / ~1.35k-token packs, and ~97% navigation reduction vs grep** — production-grade for the navigation/shortlist use case. The one hard failure (embedded SQL DDL, DCNC-005) and the hub-payload bug (now fixed) are specific, root-caused, and addressed by the P1 plan. Honest ceiling unchanged: a trusted shortlist + spans — **open the listed files; skip repo-wide grep** — not a closed-world oracle.

Raw artifacts (gitignored under `testing/dcnc/`): `results/mcp_matrix.json`, `results/live_comparison.json`, `tasks.yaml`.


## Post-improvement results (2026-10-06)

Implemented the P1–P3 plan (see `09-Production-Readiness-Plan.md`) and re-indexed dcnc offline
(harness scripts excluded via `.repopeekignore`; 116 files, 2,959 nodes).

| Metric | Before | After |
| --- | ---: | ---: |
| Mean file recall | 0.875 | **1.000** |
| Mean file precision | 0.875 | **0.938** |
| Mean mixed recall | 0.875 | **0.938** |
| Exclusion leaks | 0/8 | 0/8 |
| DCNC-005 file recall | 0.0 | **1.0** |
| `repopeek_impact` chars | 13,032 | 13,032 (bounded) |
| Live compare: gold reachable | 7/8 | **8/8** (RepoPeek ~1.1 files / ~1.36k tok vs grep 28.9 / ~65k) |

What changed and why it moved the numbers:
- **P1a (embedded SQL DDL anchoring):** `CREATE TABLE` inside a Python string is now a
  file-anchored `sql_table` node (`table.<name>`), not an unresolved external read. This made
  the dcnc `pattern_cache` table retrievable by name.
- **Finding — genuine duplicate-table ambiguity:** dcnc defines a `pattern_cache` table in
  **both** `db_manager.py` (unified cache) and `backend/core/llm/pattern_cache.py` (legacy LLM
  cache). Both legitimately "store LLM-generated patterns keyed by fingerprint_hash", so DCNC-005
  now surfaces both files (file recall 1.0, precision 0.5 against a single-file gold). This is the
  correct, honest behavior for an ambiguous schema reference, not a miss.
- **P1b + data/schema recall backstop:** DDL tasks now ensure every file defining a matching
  table is in the pack (narrow `data_intent` trigger: schema / create table / ddl / migration —
  not the over-broad "column", which had briefly pulled a 2nd file into DCNC-007).
- **P2b (honest empties):** `routes` (279 chars) and `co_changes` (140 chars) now carry an
  explanatory `note` instead of a bare empty payload on this web-less, squashed-history repo.
- **P3a/P3b:** systemic MCP payload guard (every tool ≤ 15k) and an index-time
  "Ignored (not indexed): .git, output, venv" transparency line.
- **P2a:** already covered — the Python parser emits module/class-level `variable` nodes
  (`STRATEGY_MAP` et al.); per-parameter defaults (`max_retries`) are intentionally not nodes
  (one node per parameter = inflation for little gain), so DCNC-001 symbol recall stays 0.75.

Full suite after changes: **207 passed**. Honest ceiling unchanged — a trusted shortlist + spans.
