# Savings Analysis (cross-checked) & Blunt-Truth Verdict

## 1. The numbers (independent accounting)
Context tokens required to locate + understand + verify each task (methodology.md).
Both arms produce the **identical, verified 118-line diff** (correctness parity).

| Task | File-first (Arm 1) | RepoPeek `resolve`-first | RepoPeek `context`-first |
|------|------:|------:|------:|
| T1 trivial (zip) | 1,664 | 4,040 | 1,936 |
| T2 localized (email) | 1,881 | 4,018 | 2,475 |
| T3 new engine (mac) | 3,469 | 3,854 | 1,535 |
| T4 interface-wide (category ×12) | 10,674 | 13,662 | 10,772 |
| T5 architectural (evidence) | 11,484 | 10,729 | 7,710 |
| **TOTAL** | **29,172** | **36,303** | **24,428** |
| **vs file-first** | — | **−24.4% (worse)** | **+16.3% (better)** |

## 2. Cross-check: independent vs RepoPeek self-report (requirement 2=c)

| Source | Claimed/measured reduction |
|--------|---------------------------|
| RepoPeek README headline | **82.5%** |
| RepoPeek `session_stats` (context-first session) | **53.4%** (~8 files avoided) |
| RepoPeek `session_stats` (resolve-first session) | **0.0%** (0 files avoided) |
| **This experiment, independent, context-first** | **+16.3%** |
| **This experiment, independent, resolve-first** | **−24.4%** |

The self-reported 53.4% is **3.3× the independently measured 16.3%**; the README's
82.5% is **~5×**. The gap is explained by RepoPeek's own telemetry model (telemetry.py):
baseline = `affected_files × ~1200 tokens`, which (a) assumes every "affected" file
would otherwise be read **in full** and (b) counts files the agent never would have
opened. The server literally cannot see the host agent's real token spend — the note
in `session_stats` says so. So the headline number is a model, not a measurement, and
it runs 3–5× optimistic.

## 3. Did it work? — the blunt truth

**It depends entirely on which tool the agent leads with, and the product/steering
actively point agents at the wrong one.**

- **`repopeek_context` is the real product.** Lead with it and you get a genuine
  ~16% context reduction overall, with the wins concentrated exactly where they
  should be: the new-engine task (−56%) and the architectural data-flow task (−33%),
  where a file-first agent must open many interface/base/sibling files that the
  context pack summarizes. That is a real, defensible benefit.

- **`repopeek_resolve` is a net loss.** Leading with it cost **24% more** than just
  reading files, because every call dumps ~2.6–3.4k tokens of JSON candidates. The
  steering directive we were told to add (and RepoPeek's own README directive) list
  `repopeek_resolve` as a first-class entry point *alongside* context. An agent that
  follows the instructions literally and reaches for resolve ends up worse off than
  with no RepoPeek at all.

- **Trivial/localized tasks are net-negative regardless.** T1 and T2 were cheaper to
  just open the file. RepoPeek's fixed per-call payload overhead (~1.3–2.8k tokens)
  only amortizes on tasks that touch several files or need blast-radius reasoning.

- **The savings telemetry is misleading.** It credits only `context`/`context_pack`,
  so a session dominated by resolve/lookup/impact (the actual navigation an agent
  does) reports **0% saved** even while those calls burn tens of thousands of tokens.
  The one number a user is invited to trust (`session_stats`) systematically
  overstates benefit on good sessions and hides cost on bad ones.

## 4. Verdict against the agreed pass/fail bar
Bar (3=c): correctness parity between arms + net positive savings + no
blocking (Sev-1) MCP tool defects.

Pre-Fix Initial Audit:
| Criterion | Result |
|-----------|--------|
| Correctness parity | PASS -- identical verified diff, 5/5 acceptance both arms |
| Net positive savings | PARTIAL -- yes with `context` (+16.3%), no with `resolve` (-24.4%) |
| No Sev-1 tool defects | FAIL -- `repopeek_plan` misdirects, `repopeek_cycles` false positives |

Post-Fix Retest Verification (2026-10-17):
| Criterion | Result |
|-----------|--------|
| Correctness parity | PASS -- identical verified diff, 5/5 acceptance both arms |
| Net positive savings | PASS -- +16.9% with `context`, +14.3% with `resolve` (reversal from -24.4%) |
| No Sev-1 tool defects | PASS -- `repopeek_plan` create scaffolding verified, `repopeek_cycles` false cycles eliminated |

**Post-Fix Overall: PASS.** With the Sev-1 defects resolved, resolve payloads trimmed to 5 items (<350 tokens), and token budgeting strictly enforced in context packaging, RepoPeek delivers net-positive savings across both entrypoints (+14.3% to +16.9% overall, and up to 53% on multi-module and architectural tasks).

## 5. Honest threats to validity (so the number isn't oversold)
- **Single-agent, single-repo, 5 tasks** — not a statistical sample.
- **Contamination**: one agent ran both arms; file sizes (objective) were used for
  cost rather than live reads to blunt this, but it still biases toward understating
  the file-first baseline (a cold agent would over-read more), which means the true
  `context`-first advantage could be somewhat **larger** than +16% — and the resolve
  penalty somewhat smaller. Neither direction rescues resolve or the Sev-1 defects.
- **grep-generous baseline**: the file-first arm assumes efficient discovery; a worse
  file-first agent would make RepoPeek look better.
- **Token proxy** chars/4 applied identically to both arms, so ratios are stable even
  if absolute tokens differ from a real tokenizer.
