# Important Constraints for Coding Agents

This document compiles the absolute, non-negotiable constraints that every coding agent must respect when working in this codebase.

---

## 1. Absolute Red Lines (Never Do These)

| Red Line | Why It Breaks the System |
|---|---|
| **Never edit source files in the target repository** | RepoPeek is an intelligence and context compiler, not an in-place code mutator. Mutating target code causes data loss. |
| **Never modify persisted JSON files in-place** | Partial writes corrupt `graph.json` during unexpected task termination. Always stage in `.tmp_build_<uuid>` and swap atomically. |
| **Never insert bare unnamespaced identifiers (RP-003)** | Identifiers like `next` bridge across Python and TypeScript, causing graph explosion. Always scope by language/file prefix. |
| **Never write `print()` statements to `stdout` in MCP code** | Stdio MCP uses `stdout` strictly for JSON-RPC frames. Stray prints crash client agents (Cursor, Claude Desktop). Use `sys.stderr`. |
| **Never use emojis** | Strictly forbidden across all code, docstrings, commit messages, and documentation files. |
| **Never introduce hard cloud LLM dependencies** | The pipeline must run 100% offline via `--offline` with zero network access. |
| **Never use Windows backslashes in Node IDs or spans** | All node IDs and `Span.file` values must strictly use forward slashes (`/`) for cross-platform determinism. |

---

## 2. Invariant Checklist for Every PR

Before proposing or finalizing any code change, verify that your implementation satisfies:

- [ ] **Determinism:** Identical code produces identical SHA-256 graph hashes.
- [ ] **Cycle Termination:** All graph traversals use a `visited` set and terminate in $<100$ hops.
- [ ] **Fact Verifier Compliance:** LLM-generated stories cannot override AST purity or side-effect facts.
- [ ] **Token Cap Compliance:** Context compilation respects the `budget_tokens` ceiling.
- [ ] **Test Target Invariant:** Test execution targets `python -m pytest tests`, never bare `pytest`.
- [ ] **Schema Backward Compatibility:** All new fields on Pydantic models provide defaults.
