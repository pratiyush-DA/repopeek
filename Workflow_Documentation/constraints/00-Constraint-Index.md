# Constraints and Invariants Index

This directory establishes the technical boundaries, behavioral invariants, performance budgets, security boundaries, and negative constraints governing RepoPeek.

---

## Invariant Classification Standard

Throughout this section, all rules are classified using three formal confidence levels:
1. **Verified Invariant:** Formally enforced by code checks, assertions, Pydantic validation, or automated tests.
2. **Strong Convention:** Consistently practiced architectural pattern across modules, but not mechanically guaranteed by compiler or runtime assertions.
3. **Suspected Invariant:** Inferred architectural intent visible in design or comments, but lacking definitive proof or test enforcement.

---

## Documents in this Section

| Document | Purpose |
|---|---|
| [01-Technical-Constraints.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/constraints/01-Technical-Constraints.md) | Runtime environment limits, Python versions, POSIX path normalization, schema compatibility. |
| [02-Behavioral-Invariants.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/constraints/02-Behavioral-Invariants.md) | Guaranteed system behaviors: determinism, cycle handling, atomic directory updates, AST purity. |
| [03-Performance-Constraints.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/constraints/03-Performance-Constraints.md) | Latency budgets (<50ms incremental sync), memory ceilings, token budgets (8k cap), and traversal limits. |
| [04-Security-Constraints.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/constraints/04-Security-Constraints.md) | File access boundaries, API key isolation, read-only query protections, and exclusion enforcement. |
| [05-Negative-Constraints.md](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/Workflow_Documentation/constraints/05-Negative-Constraints.md) | First-class negative knowledge: What the system must **NOT** do under any circumstances. |
