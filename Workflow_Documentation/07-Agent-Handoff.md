# Agent handoff — copy the prompt below into a new agent session

Date: 2026-10-06. This file is the onboarding packet. Do not treat older Workflow_Documentation path guesses as code truth; verify against `repopeek/`.

---

## Prompt for the next agent (copy from here)

You are taking over **RepoPeek**, a local-first Semantic Code Property Graph for AI coding agents. You are not building a SaaS, vector DB, Neo4j, IDE, or autonomous coder. Deterministic graph first; Groq stories are an optional overlay.

### What the product is (honest)

RepoPeek crawls a repo (Python, JS/TS, SQL, shell, JSON/YAML), builds a `CanonicalGraph`, optionally enriches a **top-K** of nodes with Groq, then serves lookup / blast radius / `compile_context` so agents get a **shortlist of ≤4 files plus ~40-line spans** (~1–2k tokens). It is the **primary trusted map**, not a closed-world oracle: gold files are usually in the pack; extra files remain; agents should open the listed files and skip repo-wide grep.

Latest real-world evidence (dais clone, SHA `345c3d0391d654a6f8adbedee7d51d2ab4ed59a6`): **file recall 100%**, **file precision ~33%**, **zero exclusion leaks**, grep **~47 → ~3.5 files**. Full numbers: `Workflow_Documentation/06-Dais-Real-World-Evaluation.md` (read the **Trusted-map pass** section last). Engineering history: `Workflow_Documentation/05-Engineering-Completion-Report.md`.

### Read in this order (do not dump the whole vault)

1. `.cursorrules` and `AGENTS.md` (operating rules).
2. `knowledge_vault/00-index.md` → at most 2 hops. Vault is SoT for requirements/schemas. Conventions: `knowledge_vault/_meta/conventions.md`. Changelog: `knowledge_vault/_meta/changelog.md`.
3. `Workflow_Documentation/00-README.md` then `07-Agent-Handoff.md` (this file).
4. For code edits, open the matching `knowledge_vault/features/feat-*.md` (`code_refs`) then the Python module. High-value notes: `feat-context-compiler`, `feat-intent-retrieval`, `feat-http-bridge`, `feat-semantic-enrichment`, `feat-sql-parser`, `feat-graph-construction`.
5. Workflow_Documentation under `components/`, `workflows/`, `ai-agent/` is useful narrative but **paths in `00-Documentation-Status.md` are partly stale** (blast radius is `repopeek/graph/blast_radius.py`, compiler is `repopeek/context/compiler.py`, retrieval is `repopeek/retrieval/intent.py`). Prefer `code_refs` and grep.

### Architecture (where code lives)

```
discover  →  parsers  →  GraphBuilder + identity/resolver + HTTP bridge
       →  StoryPipeline (optional Groq top-K)  →  graph.json + cache.db
       →  GraphQueryEngine (lookup, neighbors, impact, compile_context)
       →  CLI / MCP (10 tools) / viewer
```

- Identity: `lang:path::qual` vs `ext:<lang>:<ecosystem>:<name>` (`repopeek/graph/identity.py`). Never bare `next`.
- Context: file-grain rank, stem boost (LoginPage/AuthContext), exclusions, `coverage: full|partial` (`repopeek/context/compiler.py`).
- HTTP: skip identifier URLs (`downloadUrl`); require ≥1 literal path segment (`repopeek/bridges/http.py`).
- Enrich: `REPOPEEK_LLM_MAX_NODES` default 200, concurrency 2, keys `GROQ_API_KEY` + optional `_2`/`_3`. Never log or commit keys. `--offline` / `REPOPEEK_OFFLINE=1` = deterministic only.
- Index abort: >400 files or >8000 nodes (`repopeek/cli.py`). Ignore `node_modules`, `postman`, nested `repopeek`, `vendor`, `*.min.js` (`repopeek/discovery/ignore.py`).

### How we test

Always:

```text
$env:PYTHONPATH="."
.venv\Scripts\python -m pytest tests
```

**Never** bare `pytest` from repo root. `testing/` is gitignored eval workspace (dais, old da-assistant). Pytest will crawl Django tests and explode.

- Targeted: `tests/test_mvp_lock.py`, `tests/test_http_bridge.py`, `tests/test_context_compiler.py`, `tests/test_retrieval_reliability.py`.
- Vault after doc/code DoD: `python knowledge_vault/_meta/validate.py` (zero errors required).
- Frozen synthetic bench (do not overwrite `benchmarks/v1/expected/` unless asked): `python -m pytest tests` covers unit; v1 eval is `repopeek --evaluate` / evaluation module.
- Real-world dais (no commit, no push to Marketzone-DA/dais): clone at `testing/dais`. Index to `testing/dais/repopeek`. Tasks: `testing/dais/tasks.yaml`. Scripts: `testing/dais/run_mcp_matrix.py`, `testing/dais/run_live_compare.py`. After patches: `git reset --hard 345c3d0391d654a6f8adbedee7d51d2ab4ed59a6` on **dais only**; `.git/info/exclude` protects experiment files.
- Live Groq test may skip on 429. Offline index is the graduation path.

### Git and secrets

- User rule overrides `AGENTS.md` push protocol: **do not commit or push unless the user asks.**
- Never commit `.env`, keys, `testing/`, `output/`, `__pycache__`.
- Conventional commits if asked (`feat:`, `fix:`).

### Scope you must not expand

No Neo4j, vector DBs, Java/Go parsers, SaaS, whole-file default packs, SCIP as a new product. LLM must not replace AST facts.

### Known open gaps (do not “fix everything”)

File-level precision ~33% vs 40% aim; DAIS-003 symbol recall 0; some packs >2k tokens with 40-line snippets; sqlglot still Command-falls `CREATE EXTENSION`; HTTP still imperfect on odd templates; Groq stories cover ~2.5% of nodes and do not change ranking.

### Definition of done

Code + tests + vault note `last_verified` + `code_refs` + changelog line + `validate.py` clean. Update `Workflow_Documentation/06-Dais-Real-World-Evaluation.md` if you re-run dais.

---

End of prompt.

## Pointers (for humans)

| Need | Open |
| --- | --- |
| Vault start | `knowledge_vault/00-index.md` |
| Agent rules | `AGENTS.md`, `.cursorrules` |
| Testing runbook | `Workflow_Documentation/operations/03-Testing.md` |
| Dais results | `Workflow_Documentation/06-Dais-Real-World-Evaluation.md` |
| MVP lock | `Workflow_Documentation/05-Engineering-Completion-Report.md` |
| CLI / MCP | `README.md`, `repopeek/cli.py`, `repopeek/query/mcp_server.py` |
