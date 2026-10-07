# Build and Release Packaging

This document outlines the build system, package distribution artifacts, versioning policies, and pre-release verification checklist for RepoPeek.

---

## 1. Build System Specification

RepoPeek is packaged as a standard PEP 517/518 compliant Python package using `setuptools` as the build backend:

- **Build Backend:** `setuptools.build_meta` (configured in [pyproject.toml](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/pyproject.toml#L1-L3)).
- **Package Name:** `repopeek`.
- **Target Distribution:** Pure Python wheel (`py3-none-any.whl`) and Source Distribution (`.tar.gz`).
- **Binary Extension Dependencies:** None (zero C/C++ or native compiled extensions).

---

## 2. Building Distribution Artifacts

To generate distribution packages:

```bash
# Ensure build tool is installed
pip install --upgrade build

# Build sdist (.tar.gz) and wheel (.whl)
python -m build
```

The resulting artifacts are written to `dist/`:
- `dist/repopeek-0.1.0-py3-none-any.whl`
- `dist/repopeek-0.1.0.tar.gz`

---

## 3. Package Verification

Test the newly built wheel in an isolated clean environment:

```bash
# Create temporary validation venv
python -m venv test_env

# Activate test environment
# Windows:
.\test_env\Scripts\Activate.ps1
# Linux/macOS:
source test_env/bin/activate

# Install the wheel artifact
pip install dist/repopeek-0.1.0-py3-none-any.whl

# Verify CLI entry point execution
repopeek --version
repopeek --check

# Deactivate and remove test environment
deactivate
rm -rf test_env
```

---

## 4. Version Management

The version string must be kept in synchronization between two files:
1. `pyproject.toml` (`version = "0.1.0"`)
2. `repopeek/__init__.py` (`__version__ = "0.1.0"`)

### Versioning Policy (SemVer 2.0)
- **MAJOR (`X.0.0`):** Breaking changes to the CanonicalGraph JSON schema (`schema_version`), SQLite cache structure, or MCP tool definitions.
- **MINOR (`0.X.0`):** New language parsers, new lenses, new MCP tools, or performance optimizations without breaking schema backward compatibility.
- **PATCH (`0.0.X`):** Bug fixes in AST extraction, bridge route matching improvements, or retrieval algorithm tuning.

---

## 5. Pre-Release Checklist

Before tagging and releasing a new version:

- [ ] All 178 unit and integration tests pass cleanly (`pytest tests`).
- [ ] Knowledge Vault passes schema validation (`python knowledge_vault/_meta/validate.py`).
- [ ] Working tree is clean with zero uncommitted changes.
- [ ] Version string bumped in both `pyproject.toml` and `repopeek/__init__.py`.
- [ ] Offline end-to-end indexing runs without exceptions on a sample repository.
- [ ] Stdio MCP server boots and completes `tools/list` handshake.
- [ ] Changelog updated with bug fixes, features, and any schema evolutions.
