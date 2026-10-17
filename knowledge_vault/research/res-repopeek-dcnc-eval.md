---
id: res-repopeek-dcnc-eval
type: research
title: "RepoPeek Self-Evaluation on the dcnc Target Repo"
summary: Empirical A/B evaluation of RepoPeek on an external Python repo (dcnc) measuring real context savings, 16-tool MCP quality, and a product/workflow backlog.
status: completed
tags: [research, evaluation, benchmark, mcp, context-savings, dogfooding]
code_refs:
  - benchmarks/dcnc-eval/REPORT.md
  - benchmarks/dcnc-eval/savings_and_verdict.md
  - benchmarks/dcnc-eval/audit/tool_matrix.md
  - benchmarks/dcnc-eval/product_backlog.md
depends_on: ['[[feat-intent-retrieval]]', '[[feat-context-compiler]]', '[[feat-session-telemetry]]', '[[feat-graph-analysis]]', '[[feat-agent-mcp]]']
affects: []
last_verified: 2026-10-13
---
# RepoPeek Self-Evaluation on the dcnc Target Repo

Controlled A/B study running 5 progressively harder coding tasks on the external
`testing/dcnc` Python repo twice — file-first vs RepoPeek-first — plus a 16-tool MCP
audit. Full write-up and reproducible ledgers live in `benchmarks/dcnc-eval/`.

## Headline findings
- **Context savings depend on the tool.** Leading with [[feat-context-compiler]]
  (`repopeek_context`) cut context ~**16%** (independently measured). Leading with
  [[feat-intent-retrieval]] (`repopeek_resolve`) cost **24% more** than reading files,
  because its payloads run ~2.6–3.4k tokens/call. Wins concentrate on multi-file and
  architectural tasks; trivial edits are net-negative.
- **Savings telemetry overstates 3–5×.** [[feat-session-telemetry]] reported 53.4% for
  the context session (README claims 82.5%) vs the 16.3% measured here. Its model only
  credits context/pack tools, so resolve/lookup/impact sessions report 0% while still
  spending tokens.
- **Two Sev-1 defects** in the MCP surface ([[feat-agent-mcp]]): `repopeek_plan`
  misdirects "add a new engine" to editing the wrong existing class, and
  `repopeek_cycles` (part of [[feat-graph-analysis]]) reports false import cycles by
  counting inheritance/type edges — inflating the audit report to "20 cycles".
- **Correctness parity held:** both arms produced the identical, verified 118-line diff
  (5/5 acceptance each). All 16 tools run without protocol errors.

## Root causes (product)
External/unresolved symbols pollute centrality and god-nodes; edge-type conflation
creates false cycles; static analysis is blind to the registry/decorator plugin pattern
so blast radius under-counts; the intent resolver is lexical-only; token budgets are
softly enforced (context_pack overshot its budget +55%).

## Note on prior assumptions
This evaluation contradicts the parser assumption recorded under [[res-parsing-stack]]
(and Q2 in [[moc-open-questions]]): the installed package ships pure-Python/heuristic
parsers with **no tree-sitter dependency**, despite the README claiming Tree-Sitter AST
extraction. Flagged as a documentation/capability discrepancy (backlog B13).

## Verdict
Conditional pass only if constrained to `context`-first on multi-file tasks, with
resolve/plan/cycles treated as unreliable; not yet safe as the blanket "primary
navigation layer" the README markets. See the P0–P3 backlog and 4-milestone roadmap in
`benchmarks/dcnc-eval/product_backlog.md`.
