# Graph Schema Specification

#schema #json #graph #nodes #edges

## Schema Overview
This note defines the structural contract for the unified Repository Intelligence Graph. All nodes and edges generated across [[Deterministic_Substrate]] and [[Semantic_Overlay]] conform to this schema.

## JSON Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Repository Intelligence Graph Schema",
  "description": "Initial conceptual schema for MVP graph nodes and edges.",
  "node_types": {
    "Repository": {
      "purpose": "Root node for a codebase.",
      "required_fields": ["id", "name", "path"]
    },
    "File": {
      "purpose": "Represents a physical file in the repository.",
      "required_fields": ["id", "filepath", "extension"]
    },
    "Function": {
      "purpose": "Represents a parsed code function or method.",
      "required_fields": ["id", "name", "filepath", "start_line", "end_line"]
    },
    "SQLQuery": {
      "purpose": "Represents an extracted SQL statement.",
      "required_fields": ["id", "filepath", "query_text"]
    },
    "JSONConfig": {
      "purpose": "Represents a configuration object or file.",
      "required_fields": ["id", "filepath", "keys"]
    },
    "BusinessProcess": {
      "purpose": "Semantic node representing a high-level business workflow.",
      "required_fields": ["id", "name", "description", "confidence"],
      "optional_fields": ["provenance_commit"]
    },
    "Story": {
      "purpose": "Semantic node describing the narrative of how code achieves a goal.",
      "required_fields": ["id", "description", "confidence"]
    }
  },
  "edge_types": {
    "DEFINED_IN": "Links a Function/SQLQuery/JSONConfig to a File.",
    "CALLS": "Links a Function to another Function.",
    "IMPORTS": "Links a File/Function to a dependency.",
    "READS": "Links a Function to a SQLQuery, Table, or JSONConfig.",
    "IMPLEMENTS": "Links a BusinessProcess or Story to the deterministic Function(s) that execute it."
  },
  "example_business_process_node": {
    "type": "BusinessProcess",
    "id": "bp_employee_promotion",
    "name": "Employee Promotion Notification",
    "description": "Coordinates employee lookup and promotion notification.",
    "confidence": 0.92,
    "implements": [
      "function:py1.process_employees"
    ]
  }
}
```

## Related Concepts
- [[00_Index]]
- [[Deterministic_Substrate]]
- [[Semantic_Overlay]]
- [[Provenance_Engine]]
