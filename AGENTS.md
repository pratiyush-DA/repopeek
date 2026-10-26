# AGENTS.md — Agent Operating Instructions

## Knowledge Vault Protocol
- Path: `knowledge_vault/` — single source of truth for all requirements, architecture, data schemas, and design decisions.
- **Reading Protocol:** Never read the whole vault or monolithic source documents; start at `knowledge_vault/00-index.md`. Follow links to relevant MOCs and load only the specific 1–3 notes needed for your task (<= 2 hops). Check `affects` and `depends_on` frontmatter for blast radius.
- **Definition of Done:** A task is not done until:
  1. Relevant feature/component notes are created or updated.
  2. Reciprocal links (`depends_on` <-> `affects`) are maintained in frontmatter.
  3. `code_refs` and `last_verified` dates are updated on touched notes.
  4. One line is appended to `knowledge_vault/_meta/changelog.md`.
  5. `python knowledge_vault/_meta/validate.py` passes with zero errors.
- Details and templates: see `knowledge_vault/_meta/conventions.md`.
- New-agent packet: `Workflow_Documentation/07-Agent-Handoff.md`.

## Testing
- Always: `python -m pytest tests` with `PYTHONPATH=.` (Windows: `$env:PYTHONPATH="."; .venv\Scripts\python -m pytest tests`).
- **Never** run bare `pytest` from the repo root. `testing/` is gitignored (dais eval, caches) and pytest will collect foreign tests.
- After vault edits: `python knowledge_vault/_meta/validate.py` must report zero errors.

## Ponytail Protocol (Active Mode: full)
- Enforce the Decision Ladder: YAGNI -> Existing codebase -> Stdlib -> Existing dependencies -> Smallest correct implementation.
- No unrequested abstractions, speculative frameworks, or stylistic wrappers.
- Correctness boundary: Never compromise input validation, syntax error tolerance, malformed input recovery, security, or test coverage. Minimum necessary code, not minimum code at any cost.

## Git & PR Operating Protocol
- **Do not commit or push unless the user explicitly asks.** User git rules override the default “always push” loop.
- If asked to commit: stage verified files, conventional commit message (`feat:`, `fix:`), do not add `.env` or `testing/` artifacts.
- After completing a code task the vault DoD still applies even if git is not used.


<!-- REPOPEEK-RULES:START -->
# RepoPeek Code Intelligence Protocol

When RepoPeek is available in this repository, follow this evidence-based protocol for all code navigation, search, and refactoring:

## 1. Mandatory Tool Routing
- **Direct MCP Tools (Cursor, Claude Code, Windsurf, VS Code):**
  Invoke tools directly: `repopeek_lookup`, `repopeek_context`, `repopeek_resolve`, `repopeek_impact`, `repopeek_plan`.
- **Meta/Lazy MCP Dispatcher (Antigravity IDE & Wrapped Agents):**
  When tools are not in the top-level schema, invoke via the meta-tool:
  `call_mcp_tool(ServerName="repopeek", ToolName="repopeek_<cmd>", Arguments={...})`
- **Native CLI Fallback (Universal, Zero-Daemon, Offline):**
  If MCP is offline, unregistered, or returns errors, run the CLI equivalent directly via terminal:
  `repopeek --resolve "<task>"` | `repopeek --context "<task>"` | `repopeek --lookup <sym> --snippet` | `repopeek --impact <sym>` | `repopeek --plan "<task>"`

## 2. Competing Tool Constraints & Exploration Directives
- **Negative Constraint:** Treat `grep_search`, `list_dir`, and raw whole-file reading as forbidden for code search and architectural exploration UNTIL RepoPeek returns zero results or errors.
- **Zero Blind Grep:** Never begin code exploration with broad recursive greps or scanning whole directories.
- **Surgical Spans Only:** Read only the specific line ranges (`StartLine`/`EndLine`) returned by RepoPeek context slices rather than raw source files.

## 3. Hybrid Decision Ladder
- **Leaf / Single-File Edit (known file, regex tweak, typo, single localized function):**
  -> Open the file directly. Do NOT invoke RepoPeek tools on known leaf locations to avoid token framing overhead.
- **Symbol Contract Check:**
  -> Call `repopeek_lookup(query="<symbol>")` (CLI: `repopeek --lookup <symbol> --snippet`) (<70 tokens) before editing to check signature, location, and blast radius.
- **Multi-File Feature, Unfamiliar Code, or New Component:**
  -> ALWAYS call `repopeek_context(task="<task>")` (CLI: `repopeek --context "<task>"`) FIRST. It compiles AST slices, constraints, and change planning, cutting context tokens by 50-65% without reading 500-line raw files.
- **Unknown Keyword or Identifier Search:**
  -> Call `repopeek_resolve(query="<term>")` (CLI: `repopeek --resolve "<term>"`) FIRST (code-first BM25 + AST ranking).
- **Modifying Shared Interfaces, Base Classes, or Public APIs:**
  -> ALWAYS call `repopeek_impact(target="<symbol>")` (CLI: `repopeek --impact <symbol>`) FIRST to inspect upstream/downstream blast radius across call hierarchies, registries, and decorators.
- **Post-Edit Graph Synchronization:**
  -> Run `repopeek --update <file>` for sub-50ms incremental property graph synchronization.
<!-- REPOPEEK-RULES:END -->
