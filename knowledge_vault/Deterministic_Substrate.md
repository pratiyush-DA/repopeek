# Deterministic Substrate

#architecture #deterministic #ast #parser #substrate

## Overview
The deterministic substrate forms the factual foundation of the Repository Intelligence Graph. It represents ground-truth code relationships extracted mechanically through static code analysis without LLM intervention.

## Node Types
- `Repository`: Root container node.
- `File`: Physical files on disk.
- `Function`: Python function/method definitions with precise line ranges.
- `SQLQuery`: Extracted SQL queries and referenced tables/views.
- `JSONConfig`: Configuration keys and files.

## Edge Relationships
- `DEFINED_IN`: Links `Function`, `SQLQuery`, or `JSONConfig` to its parent `File`.
- `CALLS`: Direct or resolved invocations from one `Function` to another `Function`.
- `IMPORTS`: Dependency imports across files and modules.
- `READS`: Access links from a `Function` to a `SQLQuery`, database table, or `JSONConfig`.

## Guiding Principles
- **Reproducibility**: Repeated runs on identical commits must yield identical deterministic graphs.
- **Zero Hallucination**: No semantic guessing is permitted at this layer.
- **Precision**: Exact filepath and line number boundaries must be retained.

## Related Concepts
- [[Architecture_Foundations]]
- [[Graph_Schema]]
- [[Semantic_Overlay]]
- [[Phase4_PLSQL_Requirements]]
