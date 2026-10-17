# RepoPeek Product Problem Backlog & Roadmap

Derived from the dcnc evaluation (A/B experiment + 16-tool audit). Each item has
severity, user impact, rough effort (S/M/L), and a suggested fix. IDs map to the
findings (F#) and tool-matrix severities.

## P0 — Trust-breaking (fix before promoting "primary navigation layer")

| ID | Problem | Impact | Effort | Fix |
|----|---------|--------|:--:|-----|
| B1 | `repopeek_cycles` false positives: inheritance/type-ref edges counted as import cycles ("20 cycles"; `base_corrector↔corrector_interface` is not one). Propagates into `report` + `suggest_questions`. | Agents/humans chase non-existent architecture problems; erodes trust in all graph analytics. | M | Restrict cycle detection to a true `IMPORTS` edge subgraph; exclude `DEFINED_IN`/inheritance/type edges. Add a regression fixture. |
| B2 | `repopeek_plan` misdirection: "add a new MAC engine" → "modify `IPAddressEngine.validate`". Lexical resolver can't distinguish create-new from modify-existing and keyword-collides ("address"). | Agent edits the wrong file with high confidence (plan says HIGH risk, 12 nodes). Actively harmful. | L | Detect create-vs-modify intent; when the task implies a new artifact, emit scaffold steps instead of "modify nearest match". Lower confidence on weak lexical matches; show alternates. |
| B3 | Savings telemetry overstates 3–5× and only credits `context`/`context_pack`. Resolve/lookup/impact sessions report 0%. | The one metric users trust (`session_stats`, README 82.5%) is a model, not a measurement, and misleads buying/trust decisions. | M | Re-label as "modeled estimate (upper bound)"; credit a conservative per-tool saving; stop quoting a single headline %; align README with measured ranges. |

## P1 — Accuracy / signal quality

| ID | Problem | Impact | Effort | Fix |
|----|---------|--------|:--:|-----|
| B4 | External/unresolved/builtin symbols (`ext:py:builtin:len`, `ext:py:unresolved:value`) are first-class nodes and dominate `god_nodes`, pollute `data_trace`, `suggest_questions`, centrality. | "Architectural hubs" list led by `len`; nonsensical onboarding questions. | S–M | Exclude or down-weight external/unresolved nodes from centrality + god-node + question generation; keep them only for edge context. |
| B5 | Static blindness to registry/decorator plugin pattern → blast radius under-counts (`EmailEngine`: "0 callers" though used everywhere via `@register_validator`). | `impact`/`context_pack` understate real risk; dangerous false "safe to change". | L | Recognize common DI/registry/decorator patterns; add `REGISTERED_AS`/`RESOLVED_VIA` edges linking registry lookups to implementations. |
| B6 | `data_trace` low precision + junk stories: fuzzy entity match ("confidence"→34 loose readers) and templated stories with placeholder vars (`writing _, d`). | Output looks authoritative but is noisy; hard to act on. | M | Tighten entity resolution (scope/type aware); drop/clean low-signal "stories"; rank by real def-use edges. |
| B7 | `repopeek_resolve` keyword/lexical collisions ("MAC address"→IP engine) and no create-intent awareness. | Wrong primary target; cascades into plan/context. | M | Add symbol/semantic scoring beyond BM25 lexical; penalize partial-token matches; expose match rationale. |

## P2 — Cost / performance / limits

| ID | Problem | Impact | Effort | Fix |
|----|---------|--------|:--:|-----|
| B8 | `repopeek_resolve` payloads ~2.6–3.4k tokens/call; makes resolve-first net-negative vs reading files. | Defeats the whole value prop on small/medium tasks. | M | Trim resolve payload to ranked ids + 1-line reasons; move detail behind a follow-up; default to compact. |
| B9 | `context_pack` overshoots token_budget (asked 500 → 776, +55%). | Budget guarantees are a core selling point; breaking them undermines token planning. | S | Enforce hard budget: trim/sort cards to fit; truncate snippets deterministically; report actual ≤ budget. |
| B10 | `communities` truncates on a 93-file repo (>15k char tool budget) and returns 0.004 cohesion dominated by 756 YAML nodes. | Community view unusable on real repos; YAML config inflates graph. | M | Paginate/summarize communities; treat config/YAML as a separate layer; raise/stream the tool budget. |
| B11 | `co_changes` ~1s latency for an empty result (shallow clone). | Slow; discourages use. | S | Cache git log once per session; short-circuit on shallow/empty history. |
| B12 | `report`/`communities` latency ~0.6–1.2s. | Interactive feel suffers. | S–M | Precompute analytics into the index; serve from cache. |

## P3 — Packaging / DX / honesty

| ID | Problem | Impact | Effort | Fix |
|----|---------|--------|:--:|-----|
| B13 | README claims "Tree-Sitter AST extraction (36+ languages)" but no tree-sitter dependency ships; parsers are pure-Python/regex. | Capability over-claim; sets wrong expectations. | S | Correct README to describe the actual pure-Python/heuristic parsers, or add the dependency. |
| B14 | Generated MCP config uses bare `command: "repopeek"` (PATH-dependent, not venv-absolute). | MCP server won't start for users who installed in a venv/pipx-less setup. | S | Write the resolved absolute interpreter/script path (or `python -m repopeek`). |
| B15 | CLI: `--repo-path` before the `mcp` subcommand silently breaks subcommand detection. | Confusing failure during setup (the exact 1-click path the README sells). | S | Parse subcommands independent of flag order; or document/validate. |
| B16 | MCP `serverInfo.version` is `0.1.0` while package is `0.3.0`; non-ASCII `·` in stderr summary breaks Windows cp1252 consumers. | Minor correctness/telemetry confusion; cross-platform rough edges. | S | Sync version from package; ASCII-only stderr or force UTF-8. |

## Suggested roadmap (sequenced)
1. **Milestone 1 — "Stop being wrong" (P0):** B1 cycles, B2 plan create/modify intent, B3 telemetry honesty + README numbers. Ship with regression fixtures. This is the gate to honestly calling RepoPeek a navigation layer.
2. **Milestone 2 — "Trust the graph" (P1):** B4 external-node hygiene, B5 registry/decorator edges, B6/B7 resolve+data_trace precision. Turns analytics from noisy to dependable.
3. **Milestone 3 — "Pay for itself everywhere" (P2):** B8 lean resolve, B9 hard budgets, B10 communities scaling, B11/B12 perf. Makes RepoPeek-first a net win on small tasks too, not just big ones.
4. **Milestone 4 — "No surprises" (P3):** B13–B16 docs/packaging/version/encoding. Removes setup friction and over-claims.
