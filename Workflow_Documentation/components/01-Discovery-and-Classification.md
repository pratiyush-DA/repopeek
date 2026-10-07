# Component: Discovery, Classification & Hashing

## 1. Overview
The discovery subsystem crawls the target repository filesystem, applies deterministic filtering rules, detects binary content, classifies file types by extension and shebang, and calculates SHA-256 and git-compatible blob SHAs.

- **Package:** `repopeek.discovery`
- **Source Files:**
  - [`repopeek/discovery/crawler.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/crawler.py)
  - [`repopeek/discovery/classifier.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/classifier.py)
  - [`repopeek/discovery/hasher.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/hasher.py)
  - [`repopeek/discovery/ignore.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/ignore.py)
- **Primary Tests:** [`tests/test_discovery.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_discovery.py).

---

## 2. Key Classes and Functions

### `discover_repository(repo_path: Path, config=None, ignore_rules=None) -> List[DiscoveredFile]`
- Traverses `repo_path` using `os.walk(..., topdown=True)`.
- Enforces in-place alphabetical sorting on directories (`dirs.sort()`) and files (`files.sort()`) to guarantee deterministic cross-platform traversal order.
- Applies `ignore_rules.is_dir_ignored()` and `ignore_rules.is_path_ignored()`.
- Checks binary status: files with null bytes (`\x00`) in their first 8KB are tagged `skipped_binary`.
- Checks size: files exceeding `config.max_file_size_kb * 1024` are tagged `skipped_size`.
- Unsupported extensions are tagged `unsupported`.
- Returns sorted list of `DiscoveredFile` records.

### `classify_file(file_path: Path) -> FileType`
- Maps file extensions against `EXTENSION_MAP`:
  - Python: `.py`, `.pyi`
  - SQL: `.sql`
  - Shell: `.sh`, `.bash`
  - JSON: `.json`
  - YAML: `.yaml`, `.yml`
  - TypeScript: `.ts`, `.tsx`, `.mts`, `.cts`
  - JavaScript: `.js`, `.jsx`, `.mjs`, `.cjs`
- If extension is missing or unmapped, calls `check_shebang(file_path)`: inspects first line for `#!/bin/bash`, `#!/usr/bin/env python`, `#!/usr/bin/env node`.
- If neither matches, returns `FileType.OTHER`.

### `compute_file_hashes(file_path: Path) -> Tuple[str, str]`
- Returns `(sha256_hash, git_blob_sha)`.
- `sha256_hash`: Standard SHA-256 hex digest of file bytes.
- `git_blob_sha`: Git-compatible object hash calculated as `SHA1("blob <size>\0<content>")`. Matches git commit blob trees directly.

### `IgnoreRuleSet`
- Loads ignore rules from `.repopeekignore` or `.gitignore` in repository root.
- Always includes standard default ignored directories:
  `.git`, `node_modules`, `__pycache__`, `.venv`, `venv`, `.pytest_cache`, `dist`, `build`, `.egg-info`, `.idea`, `.vscode`.
- Supports directory wildcard patterns (`**/vendor/*`, `dist/`).

---

## 3. Discrepancy Note

> [!WARNING]
> **Configuration vs Classifier Discrepancy:**
> In [`repopeek/config.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/config.py#L16), the default `supported_extensions` list only contains:
> `[".py", ".sql", ".sh", ".bash", ".json", ".yaml", ".yml"]`.
> However, [`repopeek/discovery/classifier.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/discovery/classifier.py#L39) and the crawler support TypeScript (`.ts`, `.tsx`, `.mts`, `.cts`) and JavaScript (`.js`, `.jsx`, `.mjs`, `.cjs`).
> `discover_repository()` relies directly on `SUPPORTED_TYPES` in `classifier.py`, so TypeScript and JavaScript files ARE discovered and parsed. However, CLI startup messages that print `config.supported_extensions` do not display TypeScript extensions.
