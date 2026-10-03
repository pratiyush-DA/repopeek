# Vault Conventions
*This file is the living reference for how this vault is structured and maintained. Link to it from AGENTS.md.*

## Core principles
1. **One note = one concept.** Feature, component, decision, data model, or API. Never combine two.
2. **Small notes.** Target 100–400 words. Hard cap ~600 words. Split and link if exceeded.
3. **Links are the structure.** Every note must have `[[wikilinks]]`. No orphans.
4. **Bidirectional links.** If A `affects` B, B must list A in `depends_on`. Both in frontmatter and body.
5. **Link, don't duplicate.** State a fact once, link to it elsewhere.
6. **`summary` in frontmatter always.** 1–2 sentences. Sufficient to decide whether to open the note.
7. **Filename = `id`.** Use `<prefix>-<kebab-name>.md`. Stable; don't rename without updating all links.
8. **Every note reachable in ≤ 2 hops** from `00-index.md` via a MOC.
9. **`last_verified` updated** every time you confirm or change a note.
10. **Append to `_meta/changelog.md`** after every vault update.

## Prefixes
| Prefix | Type | Folder |
|--------|------|--------|
| `feat-` | feature | `features/` |
| `comp-` | component | `components/` |
| `data-` | data model | `data/` |
| `adr-NNN-` | decision (ADR) | `decisions/` |
| `con-` | constraint | `constraints/` |
| `req-` | requirement | `requirements/` |
| `flow-` | cross-component flow | `flows/` |
| `api-` | API / interface contract | `api/` |
| `term-` | glossary term | `glossary/` |
| `run-` | runbook | `runbooks/` |
| `les-` | lesson / gotcha | `lessons/` |
| `res-` | research finding | `research/` |
| `plan-` | phase plan / log | `Phase-2/` |
| `moc-` | map of content | `moc/` |

## Definition of Done (code task)
A task is NOT done until:
- [ ] Feature/component note created or updated
- [ ] Reciprocal links verified (both directions)
- [ ] `code_refs` updated if files were added/removed/renamed
- [ ] `last_verified` updated on every note touched
- [ ] One line appended to `_meta/changelog.md`
- [ ] Validation script run with zero errors

## Reading protocol (before coding)
1. Open `00-index.md` → relevant MOC → specific note(s).
2. Follow links at most **2 hops** from the target; use `summary` to decide.
3. Grep `affects:` and `depends_on:` in frontmatter for blast radius.
4. Use `code_refs` to jump to code directly.
5. Never load the whole vault or `_sources/`.
