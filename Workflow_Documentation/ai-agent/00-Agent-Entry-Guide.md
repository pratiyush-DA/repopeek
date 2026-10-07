# AI Agent Entry Guide

This document is the explicit operational playbook for autonomous AI coding agents entering the RepoPeek repository. Follow this step-by-step procedure to analyze, plan, implement, and verify modifications without human intervention.

---

## 1. The 8-Step Autonomous Action Playbook

When assigned a task or bug fix in this repository, execute the following 8 steps in strict sequence:

```text
Step 1: Read the Master README and System Overview
        ↓
Step 2: Identify the Relevant Subsystem
        ↓
Step 3: Trace the Execution Workflow
        ↓
Step 4: Inspect Ground-Truth Source Symbols
        ↓
Step 5: Review Negative and Behavioral Constraints
        ↓
Step 6: Identify and Run Target Test Suites
        ↓
Step 7: Apply the Smallest Correct Code Modification (Ponytail)
        ↓
Step 8: Execute Full Verification Protocol
```

---

## 2. Detailed Execution Steps

### Step 1: Read Context Entry Points
- Read [00-README.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/00-README.md) and [01-System-Overview.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/01-System-Overview.md) to understand overall system flow and terminology.

### Step 2: Identify the Relevant Subsystem
Determine which module owns the behavior by consulting [02-Repository-Map.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/02-Repository-Map.md):
- Ingestion & Crawling $\to$ `repopeek/discovery/`
- Parsing & AST $\to$ `repopeek/parsers/`
- Cross-Language Bridge $\to$ `repopeek/bridges/`
- Graph Construction & Lenses $\to$ `repopeek/graph/`
- Blast Radius Math $\to$ `repopeek/analysis/`
- Semantic Enrichment & LLM $\to$ `repopeek/enrichment/`
- Intent & Context Compilation $\to$ `repopeek/retrieval/`
- Storage & SQLite Cache $\to$ `repopeek/storage/`
- Watch Daemon $\to$ `repopeek/watcher/`
- Agent MCP Server $\to$ `repopeek/query/mcp_server.py`
- Web Viewer $\to$ `repopeek/viewer/`

### Step 3: Follow the Relevant Workflow Document
Open and trace the detailed sequence diagram and failure paths in `Workflow_Documentation/workflows/`:
- Adding a parser $\to$ [01-Primary-Workflow.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/01-Primary-Workflow.md)
- Modifying queries or prompt packing $\to$ [08-Query-and-Context-Compilation.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/08-Query-and-Context-Compilation.md)
- Modifying watch daemon $\to$ [09-Incremental-Watch-and-Sync.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/workflows/09-Incremental-Watch-and-Sync.md)

### Step 4: Inspect Ground-Truth Source Symbols
- Open the exact Python files and classes identified in the workflow document.
- Never assume an API signature; check the actual method declaration and type hints.

### Step 5: Check Constraints and Negative Knowledge
- Review [05-Negative-Constraints.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/constraints/05-Negative-Constraints.md) and [00-Known-Issues.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/known-issues/00-Known-Issues.md).
- Ensure your proposed change does not violate determinism, break POSIX path normalization, or introduce bare unnamespaced identifier collisions.

### Step 6: Identify Target Tests
Locate the corresponding test suite in [tests/](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/). Run it BEFORE modifying any code:
```bash
python -m pytest tests/test_<subsystem>.py
```

### Step 7: Apply Minimal Modification (The Ponytail Protocol)
- Make the smallest possible edit that solves the task.
- Zero speculative abstractions, zero unnecessary wrappers, zero added external dependencies.
- Preserve all existing comments, docstrings, and type hints.

### Step 8: Execute Full Verification
Run the verification sequence:
```bash
# 1. Run all 178 tests
python -m pytest tests

# 2. Validate Knowledge Vault
python knowledge_vault/_meta/validate.py

# 3. Verify clean git status
git status
```
*Do not conclude the task until all steps pass with zero errors.*
