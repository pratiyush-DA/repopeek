# Engineering Completion Report — MVP Lock Pass

Date: 2026-10-06

## Original architecture

Deterministic polyglot parse → CanonicalGraph → optional Groq story cascade → JSON/SQLite persistence → intent+BM25 retrieval → mathematical blast radius → context compiler → CLI/MCP/viewer.

Unresolved CALLS/IMPORTS kept bare string destinations (`next`). HTTP bridge was decorator-only. Context compiler unioned blast-radius neighbors. LLM enrichment was sequential.

## Changed architecture

- **Identity:** Unresolved/external symbols mint `ext:<lang>:<ecosystem>:<name>` (example: `ext:ts:npm:next`, `ext:py:builtin:next`). Same-language bare-name indexes only.
- **Traversal:** Fan-out cap, high-degree hub skip after 1-hop, expansion/report caps, no EXTERNAL transit, no CALLS/IMPORTS across languages.
- **HTTP:** Django `urlpatterns` + DRF `register` on the Python parser; TS wrapper inference from fetch/axios behavior.
- **Context:** Candidate generation → exclusion → neighbor relevance score → caps → package.
- **LLM:** Optional; `REPOPEEK_OFFLINE=1` / `--offline` / missing key → deterministic fallback. Bounded thread pool (`REPOPEEK_LLM_CONCURRENCY`, default **2**). Optional `GROQ_API_KEY_2` / `_3` pool for 429 isolation (RPM only rises across orgs). LLM overlay capped (`REPOPEEK_LLM_MAX_NODES`, default 200).
- **Viewer:** Server emits `label`/`language`; UI uses IBM Plex, zoom-scaled labels, tooltips.

## Why it changed

da-assistant evidence: token/exploration wins were real; graph explosion, Django blindness, wrapper blindness, and ~0.57% context precision made the product untrustworthy.

## Problems fixed (unit/integration evidence)

RP-001, RP-002, RP-003, RP-004, RP-006, RP-007 covered in `tests/test_mvp_lock.py`. RP-005 neighbor dump capped in compiler tests.

## Performance

- Pytest: **178 → 187 passed** (~38s baseline, ~73s after including new tests).
- Offline `tests/fixtures/sample_repo` graph build: **Not measured** as a published stage profile (single local timing only; not a frozen gate).
- LLM indexing profile on da-assistant: **Not measured** (full Groq enrichment not re-run in this pass).
- Parallel parse (`ThreadPoolExecutor`, results reassembled in discovery order) and parallel enrichment with locked cache/governor.

## Benchmark results

| Metric | Before | After | Change |
| --- | ---: | ---: | ---: |
| Pytest | 178 passed | 187 passed | +9 tests |
| Frozen v1 Recall/MRR | See `benchmarks/v1/expected/` | Not re-run | Not measured |
| da-assistant task success | 75% | Not measured | Not measured |
| Context recall | 86.1% | Not measured | Not measured |
| Context precision | 0.57% | Not measured | Not measured |
| Tokens/task | 59,252 total | Not measured | Not measured |
| Tool calls/task | 5.2 | Not measured | Not measured |
| Indexing time | Not measured | Not measured | Not measured |
| Query latency | Not measured | Not measured | Not measured |
| Context compile latency | Not measured | Not measured | Not measured |
| Graph explosion | 831 nodes / 190k JSON lines on `fetchClients` | Unit test: polyglot `next` no longer shares an identity; blast report bounded | Synthetic pass; da-assistant impact **Not measured** |
| Django routes detected | 0 | Fixture + parser tests pass | da-assistant `--routes` **Not measured** |
| HTTP wrappers detected | 2 of 17 | Wrapper callers tagged in tests | da-assistant **Not measured** |

## Remaining limitations

- Nested Django `include()` expansion is prefix-level, not a full urlconf graph.
- HTTP wrappers need a string-literal URL argument.
- da-assistant 12-task LLM graduation run was **not** repeated in this session.
- Frozen synthetic retrieval baseline (MRR ~0.22 in `benchmarks/v1/expected`) was preserved as a gate file, not re-executed here.
- Multi-key Groq pool not implemented (profile-first decision).

## Deleted code

None removed from the product tree. `.tmp_old_*` staging leftovers ignored via `.gitignore` rather than bulk-deleted without a reference audit.

## Added tests

`tests/test_mvp_lock.py` (P0/P1 regressions). Viewer API now asserts `label` and IBM Plex. Config includes `.ts`/`.tsx`.

## Frontend

Labels come from `NodeCard.display_label()` / `format_node_label`, not invented UI strings. Typography/zoom/tooltips updated in `repopeek/viewer/index.html`. HTTP API tests cover load + graph JSON.

## LLM / non-LLM

Deterministic core unchanged in requirement: graph/retrieval do not call Groq. Factory respects `REPOPEEK_OFFLINE`. Rate-limit/auth failures already fall back inside story generation.

## Trust assessment

If I were an AI coding agent receiving a real repository task today: **RepoPeek is more trustworthy as a navigation layer than before this pass** (namespace isolation, Django/wrappers, negatives, schema kinds). **I would not yet declare it fully reliable on precision** until the da-assistant 12-task LLM run is repeated and context precision is measured. Use `--offline` for a fast deterministic index; treat LLM enrichment as optional.
