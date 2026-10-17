# Workflow Optimization Findings

Friction observed while running this evaluation end-to-end, with a concrete
optimization for each. These are about *our development/eval workflow*, distinct
from the RepoPeek product backlog.

| # | Friction observed (evidence) | Cost | Optimization |
|---|------------------------------|------|--------------|
| W1 | **Corrupt bundled pip** in a fresh `.venv` on Python 3.10.0rc2 (`No module named 'pip._internal.utils'`); needed a `get-pip.py` bootstrap. | Blocked the clean install for several steps. | Pin a stable Python (3.10.x final, not rc2) for the project venv; add a `make venv` / bootstrap script that runs `ensurepip`+`get-pip` fallback automatically. |
| W2 | **`testing/` is gitignored and holds foreign repos** (dcnc has its own `.git`, `venv/`, `__pycache__`). dcnc has **no `.gitignore`**, so it tracks `__pycache__/*.pyc`; every import churned tracked bytecode and polluted diffs. | Had to filter `*.py` on every diff; patch picked up `.pyc`. | Add a `.gitignore` to dcnc (or the eval harness) for `__pycache__/`, `*.pyc`, `venv/`, `.repopeek/`; document "diff `-- '*.py'`" as the norm for vendored repos. |
| W3 | **PowerShell `>`/`1>` writes UTF-16** → corrupted the saved patch (`No valid patches in input`) and earlier MCP output; **CRLF vs LF** then made `git apply` fail entirely. | Lost time re-encoding + eventually re-applying edits by hand. | Standardize on `Out-File -Encoding utf8NoBOM` (or write via Python); generate patches with `git ... | Set-Content -Encoding utf8`; set `.gitattributes` `* text=auto eol=lf` for vendored repos; or just re-run deterministic edits instead of patch-replay. |
| W4 | **PowerShell has no heredoc** (`<<'PY'`); several inline Python blocks errored and dropped me into a REPL. | Repeated failed commands. | Never pipe multi-line Python via `-`; always write a `.py` helper file and run it (as the harness/ledger/compute scripts now do). |
| W5 | **PowerShell pipe to a process stdin is unreliable** for the MCP stdio server (empty output); and `Select-Object -First N` closing the pipe caused false non-zero exits. | Early MCP smoke tests looked broken when they weren't. | Use the Python subprocess harness (`mcp_client.py`) for all stdio I/O; avoid shell pipes for protocol work. |
| W6 | **Knowledge-vault DoD is heavyweight** for an eval task (create/update notes, reciprocal links, `code_refs`/`last_verified`, changelog, `validate.py`). | Overhead disproportionate to a benchmarking exercise. | Add a lightweight "experiment/eval" note type with relaxed link requirements; or a DoD checklist script that stubs the frontmatter and runs `validate.py` in one step. |
| W7 | **Large tool outputs blew the 30k console cap** (recursive `Get-ChildItem` swept the venv; big dirs). | Truncated results, extra calls. | Default to scoped, non-recursive listing; always exclude `venv/`, `.repopeek/`, `node_modules/`; prefer `grep`/glob with include patterns over raw recursion. |
| W8 | **No test suite in dcnc** despite its README claiming `tests/`; had to build an import-based `acceptance.py`. | Can't rely on target repos for correctness gates. | For eval targets, generate a minimal acceptance harness up front (as done); treat "target README claims" as unverified until checked. |
| W9 | **Re-indexing dcnc took the enrichment path over 3,173 nodes** even in `--offline`. | ~tens of seconds per re-index; discourages frequent re-index. | Cache enrichment by content hash across runs (RepoPeek has `cache.db`); expose a `--no-enrich` fast path for pure structural re-index during experiments. |
| W10 | **Experiment records risked landing in gitignored `testing/`.** | Would have lost the eval trail. | Keep all eval artifacts under `benchmarks/dcnc-eval/` (tracked), never under `testing/`; this is now the convention. |

## Highest-leverage three
1. **W2 + W10 (repo hygiene):** add `.gitignore` to vendored repos and keep eval
   artifacts out of `testing/`. Removes diff noise and protects the record.
2. **W3/W4/W5 (PowerShell I/O):** always go through Python helpers for file
   writes, patches, and stdio; stop fighting PowerShell encoding/heredoc/pipe quirks.
3. **W1/W9 (env + indexing speed):** pin a stable Python and add a fast
   no-enrich re-index path so the clean-install + re-index loop isn't a bottleneck.
