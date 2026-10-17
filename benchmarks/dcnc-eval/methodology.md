# Measurement Methodology (A/B context-cost experiment)

## What we measure
For each task we measure the **context tokens an agent must pull in to locate the
change site, understand the surrounding contract, and assess blast radius** —
i.e. the navigation + comprehension cost, which is exactly what RepoPeek claims to
cut. We do NOT reward the edit itself (both arms pay the same to type the diff).

- **Arm 1 (file-first):** the agent has no RepoPeek. It discovers the site with
  `grep`/filename search, then reads candidate files **in full** (an agent cannot
  partially trust a file it hasn't seen). Cost = Σ `chars/4` of every file it must
  open to locate + understand + verify blast radius. Over-reading (opening files
  that turn out irrelevant, or sibling/interface/base files needed to understand a
  contract) is a real, counted cost.
- **Arm 2 (RepoPeek-first):** the agent calls `repopeek_resolve` / `repopeek_context`
  / `repopeek_impact` / `repopeek_lookup` first. Cost = tokens of the tool payloads
  (measured by the harness) + tokens of only the specific files/spans RepoPeek
  cites that the agent still must open to apply the edit. Node cards and impact
  trees substitute for opening interfaces/base/sibling files.

Token proxy: `tokens ≈ characters / 4` (consistent across both arms). File sizes
are objective (`len(file_bytes)`), so the comparison does not depend on which
files this particular agent happened to read while designing the tasks.

## Savings, cross-checked (requirement 2=c)
Two independent numbers are reported side by side:
1. **Independent accounting:** `(Arm1_tokens − Arm2_tokens) / Arm1_tokens` per task
   and overall, computed from the file-size + harness ledger here.
2. **RepoPeek self-report:** `repopeek_session_stats` + the server's stderr summary
   captured during Arm 2.
Any gap between the two is reported as a finding (the telemetry is an explicit
estimate modeled at ~1200 tokens/file and only credits context/pack tools).

## Threats to validity (stated, not hidden)
- **Single-agent contamination:** both arms are executed by the same agent in one
  session, so Arm 2 benefits from repo knowledge gained in Arm 1 and task design.
  Mitigation: cost is computed from objective file sizes and a *defined* cold-agent
  discovery path, not from this agent's live reads. This still biases toward
  understating Arm 1 (a real cold agent would over-read more), so reported savings
  are a **conservative lower bound** on RepoPeek's benefit — or an honest ceiling if
  RepoPeek misdirects. Both directions are called out in the verdict.
- **Task selection:** 5 tasks on one Python repo; not a statistical sample.
- **grep baseline is generous:** we assume the file-first agent greps efficiently
  and reads only plausible candidates, which is the *best* realistic file-first case.

## Ledger
`arm1/` and `arm2/` hold per-task JSON ledgers (`task-N.json`) with the file list,
byte/token counts, tool-call payload sizes, acceptance result, and the applied diff
(`task-N.diff`). `ledger.py` recomputes totals from these so the report numbers are
reproducible.
