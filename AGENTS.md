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

