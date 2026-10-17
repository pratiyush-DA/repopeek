# RepoPeek Self-Evaluation on the dcnc Target Repo — Consolidated Report

**Date:** 2026-10-13 · **Target:** `testing/dcnc` (Data Anomaly Detector & Correction Tool, Python) · **RepoPeek:** 0.3.0 (clean install) · **Index:** 3,173 nodes / 10,648 edges, offline

This report answers, with evidence: did RepoPeek work, how much did it save, what's
wrong with each MCP tool, and what we should fix in the product and our workflow.
All raw artifacts are in this folder; numbers are reproducible via the scripts here.

---

## TL;DR (the blunt truth)
- **It conditionally works — but not the way it's sold.** With `repopeek_context` on
  multi-file tasks it cut context ~**16%** (measured independently). With
  `repopeek_resolve` (which the steering rule and README also tell agents to use
  first) it cost **24% MORE** than just reading files.
- **The headline savings number is inflated 3–5×.** README says 82.5%; RepoPeek's own
  `session_stats` said 53.4% for the context session; independent accounting says 16.3%.
- **Two tools give confidently wrong answers** (Sev-1): `repopeek_plan` (tells you to
  edit the wrong existing class when you asked to add a new one) and `repopeek_cycles`
  (reports import cycles that aren't — it counts inheritance edges).
- **Correctness parity held:** both arms produced the identical, verified 118-line diff
  across all 5 tasks (5/5 acceptance each).
- **All 16 MCP tools run** without protocol errors; the problems are quality/accuracy,
  not availability.

---

## 1. Setup (Tasks 1–2)
- Deleted stale RepoPeek artifacts from `testing/dcnc` (the `repopeek/` dir + outputs
  dumped into `output/`), preserving dcnc's own tracked data.
- Rebuilt a clean `.venv`, `pip install -e .[dev]` per README; **246/246 tests pass**.
  (Friction: the venv's bundled pip was corrupt on Python 3.10.0rc2; fixed via get-pip.)
- Re-indexed dcnc offline → `testing/dcnc/.repopeek` (3,173 nodes, 10,648 edges, 9
  lenses, 94 shards). Registered the MCP server; verified `tools/list` returns all 16.

## 2. Experiment design (Task 3)
Five tasks, increasing blast radius, frozen before either arm (`tasks.md`), each with a
deterministic acceptance check (`acceptance.py`). Cost measured as the context tokens an
agent must pull in to locate + understand + verify each change (`methodology.md`). The
diff is identical across arms; only the navigation method differs. Both arms were run and
measured; the independent ledger uses objective file sizes (`ledger.py`,
`compute_arm1.py`, `compute_arm2.py`).

| # | Task | Blast radius |
|---|------|------|
| T1 | ZIP engine accepts `12345 6789` | leaf |
| T2 | Email rejects `a..b@x.com` | localized |
| T3 | New `mac` validation engine + register | cross-module |
| T4 | Add `category` to `IValidator` + all 12 engines | interface-wide |
| T5 | Thread `evidence` field detection→report | architectural |

## 3. Results — savings, cross-checked (Tasks 4–5, 7)

| Task | File-first | `resolve`-first | `context`-first |
|------|-----:|-----:|-----:|
| T1 | 1,664 | 4,040 | 1,936 |
| T2 | 1,881 | 4,018 | 2,475 |
| T3 | 3,469 | 3,854 | 1,535 |
| T4 | 10,674 | 13,662 | 10,772 |
| T5 | 11,484 | 10,729 | 7,710 |
| **Total** | **29,172** | **36,303 (−24.4%)** | **24,428 (+16.3%)** |

| Reduction claim | Value |
|---|---|
| README headline | 82.5% |
| `session_stats` (context session) | 53.4% |
| `session_stats` (resolve session) | 0.0% |
| **Independent, context-first** | **16.3%** |
| **Independent, resolve-first** | **−24.4%** |

Wins concentrate on the new-engine (−56%) and architectural (−33%) tasks; trivial tasks
are net-negative because the fixed per-call payload (~1.3–2.8k tokens) dwarfs a small
file. Full reasoning and threats-to-validity in `savings_and_verdict.md`.

## 4. 16-tool MCP audit (Task 6)
All 16 run; details and per-tool latency/payload in `audit/tool_matrix.md`.
- **Sev-1 (wrong):** `repopeek_plan` (misdirects "add new" → modify IP engine);
  `repopeek_cycles` (false-positive import cycles; inflates `report` to "20 cycles").
- **Sev-2 (quality):** `impact`, `data_trace`, `context_pack` (budget overshoot +55%),
  `resolve` (heavy + keyword collisions), `god_nodes` (ranked by `len`), `communities`
  (truncates on 93 files), `session_stats` (savings model credits only context/pack).
- **5 root causes:** external/unresolved nodes pollute analytics; edge-type conflation
  (inheritance counted as import); static blindness to the registry/decorator pattern;
  lexical-only intent resolver; soft budget enforcement.

## 5. Verdict (Task 7)
Against the agreed bar (parity + net savings + no Sev-1):
- Correctness parity ✅ · Net savings ⚠️ (yes with context, no with resolve) · No Sev-1 ❌.
- **Overall: conditional fail as-shipped / conditional pass if constrained** to
  `context`-first on multi-file tasks, with resolve/plan/cycles treated as unreliable.

## 6. Product backlog & workflow (Tasks 8–9)
- `product_backlog.md`: B1–B16 across P0 (cycles, plan, telemetry honesty), P1 (accuracy),
  P2 (cost/perf/limits), P3 (packaging/DX), with a 4-milestone roadmap.
- `workflow_optimization.md`: W1–W10 on our own dev workflow (env/pip, repo hygiene,
  PowerShell encoding/heredoc/pipe, vault DoD weight, indexing speed).

## 7. Artifact index
- `tasks.md`, `methodology.md` — frozen design + how cost is measured.
- `acceptance.py`, `ledger.py`, `mcp_client.py`, `compute_arm1.py`, `compute_arm2.py` — harness.
- `arm1/`, `arm2/` — per-task ledgers, patches, raw tool outputs.
- `savings_summary.json`, `savings_and_verdict.md` — numbers + verdict.
- `audit/` — 16-tool audit calls, raw outputs, matrix.
- `product_backlog.md`, `workflow_optimization.md` — forward plans.

## 8. Reproduce
```powershell
# re-index dcnc (offline)
.venv\Scripts\repopeek.exe --repo-path testing/dcnc --output-dir testing/dcnc/.repopeek --offline
# recompute ledgers + savings
.venv\Scripts\python benchmarks/dcnc-eval/compute_arm1.py
.venv\Scripts\python benchmarks/dcnc-eval/compute_arm2.py
# re-run any MCP tool batch
.venv\Scripts\python benchmarks/dcnc-eval/mcp_client.py testing/dcnc benchmarks/dcnc-eval/audit/calls.json out.json
```

## 9. Post-Remediation Verification (2026-10-17)

Following implementation of the Sev-1 and Sev-2 fixes (pipx update, resolve candidate trimming, hard token budgets, import cycle restriction, decorator tracking):

| Task | File-first | `resolve`-first (Post-Fix) | `context`-first (Post-Fix) |
|------|-----------:|---------------------------:|---------------------------:|
| T1 (ZIP) | 1,664 | 1,857 | 1,895 |
| T2 (Email) | 1,881 | 2,006 | 2,329 |
| T3 (MAC engine) | 3,469 | 1,631 (-53.0%) | 1,666 (-52.0%) |
| T4 (Category x12) | 10,674 | 11,495 | 10,720 |
| T5 (Evidence flow) | 11,484 | 7,999 (-30.3%) | 7,636 (-33.5%) |
| **TOTAL** | **29,172** | **24,988 (+14.3% savings)** | **24,246 (+16.9% savings)** |

- **Resolve penalty reversed:** `resolve`-first moved from -24.4% net loss to +14.3% savings.
- **Context-first improved:** Context-first savings climbed to +16.9% overall (52.0% on cross-module T3, 33.5% on architectural T5).
- **All 16 MCP tools verified:** Handshake and tools/call succeeded across all 16 tools with zero protocol errors and zero false positive cycles.
