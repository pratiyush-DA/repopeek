# How to Safely Modify Code

This guide provides coding agents with safe modification protocols to avoid introducing regressions, breaking serialization schemas, or triggering graph corruption.

---

## 1. Pre-Modification Blast Radius Check

Before modifying any symbol or function in `repopeek/`, determine what depends on it:

```bash
# Calculate upstream blast radius
repopeek --impact "repopeek/retrieval/intent.py::IntentClassifier"
```

- If the symbol is classified as **Tier 1 (Seed)** or **Tier 2 (Direct Caller)** across multiple core workflows, modifications have high blast radius.
- Check [04-Component-Responsibilities.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/04-Component-Responsibilities.md) to understand the strict boundary contracts of that component.

---

## 2. Schema Evolution Rules ([repopeek/models/schema.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/models/schema.py))

If your change adds fields to `NodeCard`, `Edge`, `Span`, or `NodeFacts`:

1. **Mandatory Defaults:** Every new field **MUST** provide a default value (e.g. `Optional[str] = None` or `Field(default_factory=list)`). Never add mandatory positional fields without defaults.
2. **Exclude None During Dump:** When serializing, always pass `exclude_none=True` to maintain backward compatibility with older `graph.json` files.
3. **No Unhashable Types:** Any field contributing to node or graph identity must be deterministically serializable to JSON (strings, ints, floats, booleans, lists of strings). Never store live file handles, threads, or memory pointers inside models.

---

## 3. Adhering to the Ponytail Protocol

Follow the decision ladder:
- **Do not invent speculative abstractions:** If you need to parse a new configuration format, write a straightforward parser function in `repopeek/parsers/`. Do not build a generic "AbstractConfigParserPluginFactory".
- **Prefer Standard Library:** Use `pathlib`, `re`, `json`, `ast`, and `sqlite3` before proposing new `pip` dependencies.
- **Minimum Necessary Diff:** Keep changes surgical. Do not reformat unrelated lines or rename working symbols.

---

## 4. Cross-Platform Rigor

Remember that RepoPeek runs on Windows, macOS, and Linux:
- **Path Separators:** Never write `path.split("\\")` or `f"{folder}\\{file}"`. Always use `Path` methods or `str(path).replace("\\", "/")`.
- **File Encodings:** Always pass `encoding="utf-8"` when calling `open()`, `Path.read_text()`, or `Path.write_text()`.
- **Process Spawning:** Avoid raw shell commands that assume `/bin/sh` or bash syntax.

---

## 5. The Verification Sequence

Execute this exact sequence before marking any code task complete:

```bash
# 1. Run targeted test for modified module
python -m pytest tests/test_<module>.py

# 2. Run the complete 178-test suite
python -m pytest tests

# 3. Validate knowledge vault integrity
python knowledge_vault/_meta/validate.py

# 4. Confirm clean working tree
git status
```
