# Semantic Overlay

#architecture #semantic #llm #overlay #business-logic

## Overview
The semantic overlay encapsulates business logic, architectural narratives, and workflow intentions inferred by LLMs from the underlying [[Deterministic_Substrate]].

## Code → Story Pipeline
Semantic understanding is constructed hierarchically bottom-up:
1. **Raw Code Element**: Deterministic node extraction (`Function`, `SQLQuery`).
2. **Function Summary**: LLM generates succinct functional purpose based on code structure and AST.
3. **Module Flow**: LLM aggregates interactions between connected functions.
4. **Business Process / Story**: LLM clusters interrelated module activities into cohesive domain stories.

## Node Types
- `BusinessProcess`: High-level business process (e.g., employee onboarding, promotion notification, data pipeline orchestration).
- `Story`: Narrative description explaining how an operational goal is satisfied by interconnected code components.

## Edge Types
- `IMPLEMENTS`: Direct link from a `BusinessProcess` or `Story` to the deterministic `Function`(s) and queries executing it.

## Invariant Rule
Every semantic node MUST be anchored to deterministic nodes via [[Provenance_Engine]] pointers. Free-floating or ungrounded semantic nodes are disallowed.

## Related Concepts
- [[Architecture_Foundations]]
- [[Deterministic_Substrate]]
- [[Provenance_Engine]]
- [[Graph_Schema]]
