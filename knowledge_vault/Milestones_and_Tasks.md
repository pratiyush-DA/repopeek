# Milestones and Tasks

#tasks #roadmap #phases #status

## Execution Rules
- Complete exactly one task at a time.
- Do not skip ahead.
- If a task requires an undocumented architectural decision, mark it as `TBD` and pause for clarification.
- Check off tasks `[x]` only when verified complete.
- Update vault notes on each task completion.

## Phase Overview
- **Phase 1: Project Foundation**: [[Phase1_Project_Foundation]] (Active)
- **Phase 2: Repository Discovery**: File traversal and classification
- **Phase 3: Python Analysis**: AST parsing, function definitions, calls, imports
- **Phase 4: SQL Analysis**: SQL/PL-SQL parsing, queries, tables, and relationships ([[Phase4_PLSQL_Requirements]])
- **Phase 5: JSON Analysis**: Configuration parsing and schema mapping
- **Phase 6: Graph Construction**: Local NetworkX graph representation, validation against [[Graph_Schema]]
- **Phase 7: Semantic Enrichment**: LLM-driven summaries, stories, and [[Provenance_Engine]]
- **Phase 8: Query / Inspection**: CLI impact analysis and dependency traversal
- **Phase 9: Validation**: Representative repository testing and end-to-end verification

## Structural Metadata

```json
{
  "project": "Repopeek",
  "total_phases": 9,
  "total_steps": 30,
  "completed_phases": [1],
  "current_phase": 2,
  "current_step": 4,
  "phase_1_status": "completed",
  "step_1_status": "completed",
  "step_2_status": "completed",
  "step_3_status": "completed",
  "next_step": 4
}
```

## Related Concepts
- [[00_Index]]
- [[Project_Identity]]
- [[Architecture_Foundations]]
- [[Phase1_Project_Foundation]]
- [[Phase4_PLSQL_Requirements]]
