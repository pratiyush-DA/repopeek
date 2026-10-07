# Installation and Environment Setup

This guide details the steps required to set up a clean development or execution environment for RepoPeek on Windows, Linux, and macOS.

---

## 1. System Requirements

- **Operating System:** Windows 10/11, Ubuntu 20.04+, macOS 12+ (Architecture: x86_64 or ARM64).
- **Python:** Python 3.10, 3.11, or 3.12 (Python >= 3.10 required by [pyproject.toml](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/pyproject.toml#L10)).
- **Version Control:** Git 2.30+ installed and available on system `$PATH`.
- **Optional:** Groq API Key (for LLM-powered semantic story generation).

---

## 2. Virtual Environment Setup

### 2.1 Windows (PowerShell)
```powershell
# Clone repository if not already present
git clone https://github.com/pratiyush-DA/repopeek.git
cd repopeek

# Create isolated Python virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Upgrade core package managers
python -m pip install --upgrade pip setuptools wheel
```

### 2.2 Linux / macOS (Bash / Zsh)
```bash
# Clone repository
git clone https://github.com/pratiyush-DA/repopeek.git
cd repopeek

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip setuptools wheel
```

---

## 3. Dependency Installation

RepoPeek can be installed in editable development mode with development dependencies:

```bash
pip install -e ".[dev]"
```

### 3.1 Core Dependency Manifest
From [pyproject.toml](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/pyproject.toml#L20-L28):
- `networkx>=3.0`: In-memory graph algorithms, cycle detection, path traversals.
- `sqlglot>=25.0.0`: Transpilation and relational AST extraction.
- `sqlparse>=0.5.0`: Non-validating lexical SQL query tokenization fallback.
- `jsonschema>=4.20.0`: JSON schema draft validation.
- `pydantic>=2.5.0`: Schema validation and high-performance serialization.
- `pyyaml>=6.0.0`: YAML configuration parsing.
- `ruamel.yaml>=0.18.0`: Round-trip YAML handling with comment preservation.

### 3.2 Optional Development Packages
- `pytest>=7.0.0`: Test runner and evaluation suite.

---

## 4. Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GROQ_API_KEY` | Optional | None | API key for Groq Cloud LLM enrichment (`qwen/qwen3.8-27b`) |
| `REPOPEEK_OFFLINE` | Optional | `0` | If set to `1`, forces offline enrichment mode |
| `REPOPEEK_LOG_LEVEL`| Optional | `INFO` | Console logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Setting Environment Variables:
- **Windows PowerShell:**
  ```powershell
  $env:GROQ_API_KEY = "gsk_your_actual_key_here"
  ```
- **Linux/macOS Bash:**
  ```bash
  export GROQ_API_KEY="gsk_your_actual_key_here"
  ```

---

## 5. Verification

To verify that the installation succeeded and the entry points are correctly bound:

```bash
# Verify CLI entry point
repopeek --version

# Run non-destructive environment check
repopeek --check
```

Expected output:
```text
repopeek 0.1.0
Environment check: OK (Python 3.10+, Dependencies satisfied)
```
