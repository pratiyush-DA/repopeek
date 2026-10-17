# 16-Tool MCP Audit — against the freshly-indexed dcnc graph

All 16 tools were invoked over one stdio MCP session (`audit/calls.json` →
`audit/audit_out.json`). "Runs" = returns a well-formed MCP result without error.
Correctness/quality was judged by inspecting each payload against ground truth in
the dcnc source. Severity: **Sev-1** = wrong/misleading output an agent would act
on; **Sev-2** = materially degraded quality/usefulness; **Sev-3** = minor/cosmetic.

| # | Tool | Runs | Latency | Payload (tok) | Verdict | Severity |
|---|------|:----:|--------:|--------------:|---------|:--------:|
| 1 | `repopeek_context` | ✅ | 253 ms | ~1491 | Good. Lean, cited files + spans. Est-tokens line vs budget is an estimate. | Sev-3 |
| 2 | `repopeek_plan` | ✅ | 71 ms | ~488 | **Wrong.** For "add a NEW MAC engine" it says modify `IPAddressEngine.validate` (keyword collision on "address"). Can't tell create-new from modify-existing; misdirects the agent. | **Sev-1** |
| 3 | `repopeek_impact` | ✅ | 24 ms | ~3264 | Works; finds 58 affected. Mixes the target's own members into "affected"; misses registry/dynamic dependents (plugin calls invisible to static graph). Heavy payload. | Sev-2 |
| 4 | `repopeek_lookup` | ✅ | 3 ms | ~602 | Good. Accurate node card + snippet. Fast. | Sev-3 |
| 5 | `repopeek_neighbors` | ✅ | <1 ms | ~1227 | Good. Correct IMPORTS/DEFINED_IN edges with confidence + citations. | — |
| 6 | `repopeek_data_trace` | ✅ | 4 ms | ~2845 | Low precision. Entity "confidence" fuzzy-matched to `ext:...:detection.confidence`, 34 "readers" loosely related; stories contain junk var names (`writing _, d`). | Sev-2 |
| 7 | `repopeek_context_pack` | ✅ | 40 ms | ~777 | **Overshoots budget**: asked 500, returned ~776 (+55%). "0 callers/readers" wrong for a registry-used class (static blind to decorator registry). | Sev-2 |
| 8 | `repopeek_routes` | ✅ | 29 ms | ~70 | Correct. Empty + honest note (dcnc has no web layer). | — |
| 9 | `repopeek_co_changes` | ✅ | **1004 ms** | ~34 | Correct empty result + honest note (shallow clone), but ~1s for an empty answer — shells git history per call. | Sev-3 |
| 10 | `repopeek_resolve` | ✅ | 61 ms | ~2777 | Works but **heavy** (~2.8k/call) and keyword-collides (MAC "address" → IP engine). It's the tool the steering rule promotes first, yet costs the most and is credited 0 savings. | Sev-2 |
| 11 | `repopeek_god_nodes` | ✅ | 14 ms | ~363 | **Noisy.** Ranking topped by `ext:py:builtin:len` (339) and `ext:py:unresolved:value` (228) — externals/builtins pollute the "architectural hub" list. | Sev-2 |
| 12 | `repopeek_cycles` | ✅ | 15 ms | ~2015 | **False positives.** Reports `base_corrector → corrector_interface → base_corrector` as an import cycle, but `corrector_interface` imports only stdlib. Counts inheritance/type edges as imports; "20 cycles" inflated. | **Sev-1** |
| 13 | `repopeek_communities` | ✅ | 638 ms | ~590* | **Truncated** on a 93-file repo (payload >15k budget → preview only). Largest community cohesion 0.004, dominated by 756 YAML config nodes. | Sev-2 |
| 14 | `repopeek_suggest_questions` | ✅ | 116 ms | ~268 | Propagates upstream noise: asks "God node `len`… violate SRP?" and cites the false cycle. Some items nonsensical. | Sev-2 |
| 15 | `repopeek_report` | ✅ | 1205 ms | ~3266 | Comprehensive and useful, but surfaces inflated "Import Cycles = 20" and noisy god nodes. Slowest tool. | Sev-3 |
| 16 | `repopeek_session_stats` | ✅ | <1 ms | ~536 | Honest (clear estimate note). But the savings MODEL credits only context/pack, so resolve/lookup/impact-heavy sessions show ~0% — misleading as a headline "savings" number. | Sev-2 |

\* truncated preview, not full payload.

## Summary
- **16/16 tools run without protocol errors** — the MCP surface is complete and stable.
- **2 Sev-1 (wrong output an agent acts on):** `repopeek_plan` (misdirects "add new" to editing the wrong existing class), `repopeek_cycles` (false-positive import cycles, propagated into `report` + `suggest_questions`).
- **7 Sev-2 (quality):** impact (noise + registry blindness), data_trace (precision/story quality), context_pack (budget overshoot + static blindness), resolve (payload weight + keyword collision), god_nodes (builtin/unresolved pollution), communities (truncation + 0 cohesion), session_stats (savings model only credits context/pack).
- **Cross-cutting root causes:**
  1. **External/unresolved symbols** (`ext:py:unresolved:*`, builtins) are first-class graph nodes and pollute centrality, god-nodes, data-trace, and questions.
  2. **Edge-type conflation:** inheritance/type-reference edges are treated as import edges → false cycles.
  3. **Static blindness to the registry/decorator plugin pattern** → under-counted blast radius (0 callers for used classes).
  4. **Intent resolver is keyword/lexical** → "MAC address" → IP engine; cannot distinguish create-new vs modify-existing.
  5. **Budget/limit enforcement is soft** (context_pack overshoots; communities truncates).
