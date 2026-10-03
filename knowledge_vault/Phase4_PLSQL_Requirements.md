# Phase 4 — Oracle PL/SQL Parser Requirements

#phase4 #sql #plsql #oracle #requirements #parser #architecture

## Overview
During Phase 4 (SQL Analysis), the Repository Intelligence Engine must analyze complex Oracle PL/SQL database procedures and stored scripts alongside standard SQL statements.

## Key Requirements & Parser Capabilities
1. **Oracle PL/SQL Syntax Support**:
   - Stored procedures, functions, packages, and anonymous PL/SQL blocks.
   - Dynamic SQL execution and cursor loops.
2. **Exception Blocks Handling**:
   - `EXCEPTION WHEN OTHERS THEN`, specific named exceptions, and nested exception handlers must be parsed without breaking the AST or query boundary detection.
3. **String Concatenation Handling**:
   - Dynamic SQL constructed using Oracle string concatenation operator `||` (e.g. `'DROP TABLE ' || table_name || ' PURGE;'`).
   - Resolution or tokenization of target table names when constructed dynamically.
4. **Target Schema & Table Identification**:
   - Fully qualified table references, notably including data warehouse / batch processing tables like `CORE_SCHEMA.BATCH_JOBS`.
   - Identification of batch clean-up scripts (e.g., `CLEANUP_TEMP_TABLES` routines) and transient table management.

## Structural Metadata Specification

```json
{
  "parser_target": "Oracle PL/SQL",
  "phase": "Phase 4 - SQL Analysis",
  "dialects": ["Oracle 12c+", "ANSI SQL"],
  "critical_constructs": [
    "EXCEPTION blocks",
    "String concatenation operator (||)",
    "DDL in stored procedures (EXECUTE IMMEDIATE)",
    "DML on batch/staging tables"
  ],
  "sample_table_targets": [
    "CORE_SCHEMA.BATCH_JOBS"
  ],
  "sample_script_patterns": [
    "CLEANUP_TEMP_TABLES"
  ],
  "graph_extraction": {
    "node_type": "SQLQuery",
    "edge_types": ["READS", "DEFINED_IN"]
  }
}
```

## Related Concepts
- [[00_Index]]
- [[Deterministic_Substrate]]
- [[Graph_Schema]]
- [[Milestones_and_Tasks]]
