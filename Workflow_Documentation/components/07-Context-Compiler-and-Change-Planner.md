# Component: Context Compiler & Change Planner

## 1. Overview
The Context Compiler transforms user tasks into compact, structured Markdown context packages (<500 to 1500 tokens) designed for autonomous AI coding agents. It enforces structural constraints, calculates mathematical blast radius reachability, and constructs step-by-step, risk-assessed engineering change plans.

- **Package:** `repopeek.context`
- **Source File:** [`repopeek/context/compiler.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/context/compiler.py)
- **Primary Tests:** [`tests/test_context_compiler.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_context_compiler.py).

---

## 2. Progressive Disclosure Levels

The compiler renders markdown packages according to the specified `--level` (1, 2, or 3):

| Level | Name | Target Token Range | Contents |
|---|---|---|---|
| **Level 1** | Executive Brief | 250 - 400 tokens | Task summary, top entrypoint symbols, direct blast radius count, high-level change plan. |
| **Level 2** | Standard Coding Context | 600 - 1000 tokens | Entrypoints with full signatures and stories, partitioned direct and indirect blast radius nodes, multi-tier constraints, and actionable change plan. |
| **Level 3** | Full Context with Snippets | 1200 - 1800 tokens | Includes everything in Level 2 plus exact physical source code slices extracted from disk for entrypoints and direct targets, enabling zero-file-read edits. |

---

## 3. Multi-Tier Constraint Extraction (`ConstraintSet`)

The compiler automatically extracts structural and semantic boundaries from AST facts:

```text
ConstraintSet:
├── parameter_constraints:
│   └── "Must accept parameter 'payload' (type bytes)"
├── return_constraints:
│   └── "Must return 'Invoice' instance"
├── exception_constraints:
│   └── "Must preserve raising 'ParseError' on invalid XML buffers"
├── schema_constraints:
│   └── "Relies on schema table 'invoices'"
└── behavioral_invariants:
    ├── "MUST NOT modify files matching exclusion rule: 'shipping/'"
    └── "Verified caller contract across 3 dependent modules"
```

---

## 4. Engineering Change Plan Generator (`ChangePlan`)

The change plan engine assesses blast radius risk and compiles a 3-phase execution plan:

### Risk Assessment Rules
- `Risk Level = HIGH`: If the blast radius impacts $> 1$ database table, $> 5$ callers, or involves cross-language boundaries.
- `Risk Level = MEDIUM`: If callers $> 2$ or modifies shared utilities.
- `Risk Level = LOW`: If isolated to a single file with $\le 2$ callers.

### 3-Phase Plan Structure
1. **Phase 1: Pre-Change Verification (`pre_checks`):**
   - Discovers test files connected via `TESTS_CODE` edges.
   - Formulates commands to run baseline tests before modifying code.
2. **Phase 2: Actionable Implementation Steps (`steps`):**
   - Step 1: Core modification on target entrypoint (with file citation).
   - Step 2..N: Downstream caller updates within direct blast radius.
   - Step N+1: Database table or configuration updates.
3. **Phase 3: Post-Change Regression Validation (`post_checks`):**
   - Identifies downstream test suites and commands to ensure zero regression.

---

## 5. Token Budget Governance

In [`ContextCompiler.compile()`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/context/compiler.py#L220):
1. Allocates tokens across sections:
   - Header & Metrics: ~50 tokens
   - Entrypoints: ~200 - 400 tokens
   - Direct Blast Radius: ~250 - 500 tokens
   - Indirect Blast Radius: ~150 - 300 tokens
   - Constraints: ~100 - 200 tokens
   - Change Plan: ~200 - 350 tokens
2. If total estimated tokens exceed `token_budget` (default 1500):
   - Lower-ranked indirect blast radius nodes are iteratively pruned.
   - Snippet lengths are truncated to `max_lines = 15`.
   - Never prunes target entrypoints or direct blast radius nodes.
