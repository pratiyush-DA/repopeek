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
