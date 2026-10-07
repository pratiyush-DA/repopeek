# Component: Polyglot Parsers

## 1. Overview
The parsers subsystem provides deterministic syntactic extraction across Python, TypeScript, JavaScript, SQL, Shell, JSON, and YAML. It translates language-specific syntax into canonical `NodeCard` and `Edge` objects with line spans and AST facts.

- **Package:** `repopeek.parsers`
- **Source Files:**
  - [`repopeek/parsers/base.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/base.py)
  - [`repopeek/parsers/python.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/python.py)
  - [`repopeek/parsers/typescript.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/typescript.py)
  - [`repopeek/parsers/sql.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/sql.py)
  - [`repopeek/parsers/shell.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/shell.py)
  - [`repopeek/parsers/config.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/parsers/config.py)
- **Primary Tests:**
  - [`tests/test_python_parser.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_python_parser.py)
  - [`tests/test_typescript_parser.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_typescript_parser.py)
  - [`tests/test_polyglot_parsers.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_polyglot_parsers.py)

---

## 2. Parser Implementations

### 2.1 Python Parser (`PythonParser`)
- **Engine:** Standard library `ast`.
- **Extracted Nodes:**
  - `file`: Module root card.
  - `class`: Class declaration, base classes (`INHERITS`), decorators.
  - `function` / `method`: Functions, synchronous and asynchronous, parameter signatures, return type annotations, docstrings.
  - `variable`: Module-level constants, class attributes, mutated variables.
- **Extracted Edges:**
  - `DEFINED_IN`: Structural parent-child relationships.
  - `CALLS`: Method and function calls (resolves qualified and bare calls).
  - `IMPORTS`: `import X` and `from X import Y`.
  - `READS` / `WRITES`: Variable mutations, attribute lookups, SQL table reads/writes.
  - `RAISES`: `raise ExceptionType(...)`.
  - `CATCHES`: `except ExceptionType as e:`.
  - `EMBEDS_SQL`: Scans string literals using `SQL_KEYWORD_PATTERN`; parses SQL via `sqlglot` to extract referenced tables.
- **Syntax Error Resilience:**
  - Catches `ast.SyntaxError`.
  - Dispatches to `_parse_fallback()`: uses regex patterns (`FALLBACK_FUNC_RE`, `FALLBACK_CLASS_RE`, `FALLBACK_IMPORT_RE`) to recover partial symbol cards.

### 2.2 TypeScript / JavaScript Parser (`TypeScriptParser`)
- **Engine:** Pure Python regex and lexical scanner (zero npm/Node.js dependencies).
- **Extracted Constructs:**
  - Classes: `class Foo extends Bar implements Baz`.
  - Interfaces: `interface UserState { ... }`.
  - Type Aliases: `type UserID = string;`.
  - Functions: `function test()`, arrow functions `const doWork = async (x: int) => { ... }`, function expressions.
  - Methods: Class constructor, public/private/static/async methods.
  - Imports: `import { X } from "Y"`, `import * as X from "Y"`, `require("Y")`, dynamic `import("Y")`.
  - Client HTTP Calls: Scans for `fetch("...")`, `axios.get("...")`, `apiClient.post("...")`, extracting HTTP methods and raw paths into `facts.reads` (e.g. `HTTP:/api/users`).
  - Cyclomatic Complexity: Computed via `COMPLEXITY_RE` matching branching keywords (`if`, `for`, `while`, `switch`, `case`, `catch`, `?`, `&&`, `||`).
  - JSDoc: Parsed and assigned as initial story text.

### 2.3 SQL Parser (`SqlParser`)
- **Engine:** `sqlglot` with dialect fallback.
- **Supported Dialects:** Oracle, Postgres, ANSI.
- **Extracted Entities:**
  - `sql_table`: Tables created (`CREATE TABLE`), updated, or queried.
  - `sql_query`: SQL statements.
  - `WRITES`: `INSERT INTO`, `UPDATE ... SET`, `MERGE INTO`.
  - `READS`: `SELECT ... FROM`, `JOIN ... ON`.
- **Fallback:** If all dialects fail to parse via SQLGlot, uses regex pattern matching (`_fallback_extract()`) to capture `CREATE TABLE`, `SELECT FROM`, and `INSERT INTO`.

### 2.4 Shell Parser (`ShellParser`)
- **Engine:** Standard library `shlex` and regex.
- **Extracted Entities:**
  - `file`: Shell script root.
  - `command`: Command segments separated by `|`, `;`, `&&`, `||`.
  - `RUNS_SCRIPT`: Invocations of target scripts (`python script.py`, `bash run.sh`, `./deploy.sh`).
  - `WRITES`: Environment variable assignments (`export VAR=val`, `VAR=val`).
  - `READS`: Environment variable expansions (`$VAR`, `${VAR}`).

### 2.5 Config Parsers (`JsonConfigParser`, `YamlConfigParser`)
- **Engine:** `json` (stdlib) and `yaml` (`pyyaml`).
- **Behavior:** Flattens nested configurations using dot notation:
  ```json
  {"database": {"pool": {"max_connections": 20}}}
  ```
  Produces:
  - `json:<path>::database.pool.max_connections` (kind: `json_config`, sig: `database.pool.max_connections = 20`).
- **Resilience:** JSON and YAML decode errors are trapped and appended to `ParseResult.errors` without halting indexing.
