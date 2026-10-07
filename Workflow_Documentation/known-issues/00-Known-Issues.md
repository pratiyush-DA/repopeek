# Known Issues and Defect Ledger

This ledger tracks defects found during documentation audit and the da-assistant real-world experiment. Status below reflects the MVP lock engineering pass (2026-10-06).

---

## 1. Confirmed Bugs

### Issue RP-001: Django Declarative Route Registrations Missed by HTTP Bridge
- **Status:** Addressed in MVP lock. `PythonParser._attach_django_routes` tags `urlpatterns` (`path`, `re_path`, `url`, `include`) and DRF `router.register`. Bridge scans file/class/function nodes for `ROUTE:` facts.
- **Remaining limitation:** Nested `include()` modules are recorded as prefix routes on the parent file; they are not always fully expanded into the included urlconf.

### Issue RP-002: Custom Fetch / Axios Wrappers Missed by TypeScript Parser
- **Status:** Addressed. Functions whose bodies call `fetch`/`axios` are treated as HTTP wrappers; callers with URL-like first arguments receive `HTTP:` facts.
- **Remaining limitation:** Wrappers that pass URLs only via object fields (`{ url: ... }`) or template concatenation without a string literal may still be missed.

### Issue RP-003: Unnamespaced Identifier Collisions Cause Giant Component Merges
- **Status:** Addressed. Unresolved CALLS/IMPORTS destinations mint `ext:<lang>:<ecosystem>:<name>` identities. Bare-name resolution is same-language only. Blast radius caps fan-out, high-degree hubs, expansion, and report size; EXTERNAL symbols are not used as transit hubs.
- **Remaining limitation:** Same-language duplicate names can still be AMBIGUOUS (first sorted id wins).

### Issue RP-004: False Database Schema Constraints via Naive Substring Matching
- **Status:** Addressed. Schema tagging uses `is_sql_table_kind(node.kind)` in compiler, blast radius, and `context_pack`. Path: [repopeek/context/compiler.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/context/compiler.py).

### Issue RP-007: BM25 Treats Negative Exclusions as Positive Relevance Signals
- **Status:** Addressed. Exclusion regex covers `MUST NOT edit`, `do not touch`, and `without modifying`; exclusion spans are masked before positive tokenization; FTS terms drop exclusion tokens; resolver hard-filters excluded ids/paths.

### Issue RP-005 / RP-006
- **RP-005 Status:** Addressed internally via neighbor relevance filtering in `ContextCompiler` and ranked `context_pack` neighbors. da-assistant precision **re-measurement not completed** in this pass.
- **RP-006 Status:** Application-intent scoring heavily penalizes YAML/Docker/config nodes; infrastructure intent still prefers them.

---

## 2. Documentation Discrepancies

### Issue RP-008: Outdated Root Documentation in `README.md`
- **Location:** `README.md` vs [repopeek/query/mcp_server.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/query/mcp_server.py) and [repopeek/llm/groq.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/llm/groq.py)
- **Discrepancy 1 (MCP Tools):** `README.md` claims RepoPeek exposes 5 MCP tools (`lookup`, `neighbors`, `impact`, `data_trace`, `context_pack`). The actual server implementation exposes **10 tools** (adding `repopeek_context`, `repopeek_plan`, `repopeek_routes`, `repopeek_co_changes`, `repopeek_resolve`).
- **Discrepancy 2 (LLM Model):** `README.md` claims Groq uses `llama-3.1-8b-instant`. The actual code configures `qwen/qwen3.8-27b` and `openai/gpt-oss-120b`.
- **Status:** Documented discrepancy. Code is ground truth.
- **Impact:** Medium. Misleads developers and agents relying on README for tool discovery.

---

## 3. Technical Debt

### Issue RP-009: Supported Extensions Omission in Config
- **Location:** [repopeek/config.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/config.py#L16) vs [repopeek/discovery/classifier.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/classifier.py#L12)
- **Observed Behavior:** `RepopeekConfig.supported_extensions` defaults to `[".py", ".sql", ".yaml", ".yml", ".json", ".dockerfile", ".env"]`, omitting `.ts`, `.tsx`, `.js`, and `.jsx`. However, `classifier.py` and `GraphBuilder` actively parse TypeScript.
- **Impact:** If an external caller relies strictly on `config.supported_extensions`, TypeScript files might be unintentionally bypassed.
- **Confidence:** High.

---

## 4. Architectural Risks

### Issue RP-010: In-Memory NetworkX Scaling Ceiling
- **Location:** [repopeek/models/schema.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py)
- **Risk:** Storing the entire code property graph in an in-memory NetworkX `DiGraph` will encounter Python heap exhaustion (OOM) on massive multi-million-line monorepos (e.g. >500,000 AST nodes).
- **Current Status:** Not observed in repositories under 50,000 LOC, but constitutes a known ceiling for enterprise-scale monorepos.
- **Confidence:** Medium (Theoretical architectural risk).
