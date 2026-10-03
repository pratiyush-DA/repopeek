# Architecture Foundations

#architecture #pipeline #design-principles

## High-Level Architecture Pipeline

```text
Repository
    ↓
File Discovery (Phase 2)
    ↓
Language / File Classification (Python, SQL, JSON)
    ↓
Deterministic Parsing (Phases 3, 4, 5)
    ├── Python → AST / Functions / Calls / Imports
    ├── SQL → Queries / Tables / Relationships
    └── JSON → Configuration / Keys
    ↓
Deterministic Graph (Phase 6)
    ↓
Semantic Enrichment (Phase 7)
    ↓
Semantic Overlay
    ↓
Unified Repository Graph
    ↓
Query / Agent Interface (Phase 8)
```

## Architectural Layers
1. **Substrate Layer**: [[Deterministic_Substrate]] handles deterministic, statically analyzed code facts. Never relies on LLMs for facts extractable via static analysis.
2. **Overlay Layer**: [[Semantic_Overlay]] houses business narratives and workflow abstractions (`BusinessProcess`, `Story`).
3. **Traceability**: [[Provenance_Engine]] guarantees that every semantic node links directly to source code coordinates and confidence metrics.
4. **Data Contract**: Defined in [[Graph_Schema]].

## Connected Notes
- [[00_Index]]
- [[Project_Identity]]
- [[Deterministic_Substrate]]
- [[Semantic_Overlay]]
- [[Provenance_Engine]]
- [[Graph_Schema]]
- [[Phase4_PLSQL_Requirements]]
