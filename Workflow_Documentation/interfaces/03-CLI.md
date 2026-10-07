# Command-Line Interface (CLI) Reference

RepoPeek exposes a single, unified CLI entry point via [repopeek/cli.py](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/cli.py).

---

## 1. Invocation Syntax

```bash
repopeek [GLOBAL_OPTIONS] [COMMAND_OR_QUERY_FLAGS]
```
Alternatively:
```bash
python -m repopeek.cli [GLOBAL_OPTIONS] [COMMAND_OR_QUERY_FLAGS]
```

---

## 2. Option Reference

### 2.1 Global Configuration Options

| Option | Type | Default | Description |
|---|---|---|---|
| `-v`, `--version` | Flag | N/A | Display version string and exit |
| `--repo-path <PATH>` | Path | `.` | Target repository directory to inspect |
| `--output-dir <PATH>` | Path | `./output` | Destination directory for `.repopeek/` graph artifacts |
| `--config <PATH>` | Path | `None` | Path to JSON configuration file overriding defaults |
| `--sql-dialect <NAME>` | String | `oracle` | Default SQL dialect for AST parsing (`oracle`, `postgres`, `mysql`, `snowflake`, `bigquery`) |
| `--check` | Flag | `False` | Validate configuration, environment, and exit without indexing |
| `--offline` | Flag | `False` | Run semantic enrichment with deterministic AST stories (zero LLM calls) |
| `--dry-run` | Flag | `False` | Estimate token consumption and cost without invoking LLM APIs |

### 2.2 Server and Daemon Modes

| Option | Type | Default | Description |
|---|---|---|---|
| `--serve-mcp` | Flag | `False` | Run stdio JSON-RPC MCP server for autonomous AI coding agents |
| `--view` | Flag | `False` | Launch interactive web viewer in default web browser |
| `--port <PORT>` | Integer | `8765` | TCP port for the local web viewer HTTP server |
| `--watch` | Flag | `False` | Start continuous background file watch daemon for real-time `<50ms` updates |
| `--watch-interval <SEC>` | Float | `1.0` | Polling interval in seconds for the watch daemon |

### 2.3 Query and Retrieval Commands

| Option | Type | Description |
|---|---|---|
| `--lookup <QUERY>` | String | Query node card metadata, facts, and span by symbol name or qualified ID |
| `--impact <QUERY>` | String | Calculate multi-hop blast radius, risk scores, and tier breakdown |
| `--trace <ENTITY>` | String | Trace def-use data flow for a variable, parameter, or database table |
| `--pack <TARGETS...>` | List[String] | Generate budget-governed context pack for specific targets |
| `--snippet` | Flag | Include full code snippets in lookup and context pack outputs |
| `--resolve <TASK>` | String | Resolve a natural language task to candidate symbols using hybrid retrieval |
| `--explain <TASK>` | String | Diagnostic retrieval debugging (token normalization, candidates, scores) |
| `--context <TASK>` | String | Compile task-driven context package with blast radius and constraints |
| `--plan <TASK>` | String | Generate risk-assessed, step-by-step engineering change plan |
| `--level <1\|2\|3>` | Integer | Progressive disclosure level (`1`: brief, `2`: standard, `3`: full code) |
| `--budget <TOKENS>` | Integer | Token budget cap for context compilation (default: 1500) |
| `--co-changes <TARGET>` | String | Query git co-change relationships and probabilities for a target file/symbol |
| `--routes` | Flag | Discover server HTTP endpoints, client calls, and cross-boundary linkages |
| `--update <FILE>` | Path | Perform an incremental graph update for a single modified file |

### 2.4 Obsidian Vault Export and Reading

| Option | Type | Description |
|---|---|---|
| `--export-obsidian [PATH]` | String | Export canonical graph into an Obsidian vault (`default` auto-detects) |
| `--open` | Flag | Open the exported vault in Obsidian Desktop via `obsidian://` URI |
| `--read-obsidian <SYMBOL>` | String | Query symbol documentation directly from an exported Obsidian vault |
| `--vault-path <PATH>` | Path | Path to the target Obsidian vault directory for reading |

### 2.5 Evaluation and Benchmarking Suite

| Option | Type | Default | Description |
|---|---|---|---|
| `--evaluate` | Flag | `False` | Run comprehensive evaluation and benchmark suite |
| `--dataset <PATH>` | Path | `benchmarks/v1/tasks.yaml` | Path to benchmark tasks dataset (YAML or JSON) |
| `--output <PATH>` | Path | `benchmark-results.json` | Destination path for machine-readable JSON evaluation results |
| `--report` | Flag | `False` | Generate human-readable Markdown evaluation report |

---

## 3. Practical Usage Examples

### 3.1 Full Repository Indexing (Offline)
```bash
repopeek --repo-path . --output-dir .repopeek --offline
```

### 3.2 Symbol Lookup with Source Snippet
```bash
repopeek --repo-path . --lookup "GraphBuilder" --snippet
```

### 3.3 Multi-Hop Blast Radius Calculation
```bash
repopeek --repo-path . --impact "repopeek/models/schema.py::NodeCard"
```

### 3.4 Context Package Compilation for a Task
```bash
repopeek --repo-path . --context "Fix memory leak in watch daemon" --level 2 --budget 2000
```

### 3.5 Generating an Engineering Change Plan
```bash
repopeek --repo-path . --plan "Add support for C# / .NET AST parsing"
```

### 3.6 Launching the Stdio MCP Server (Agent Mode)
```bash
repopeek --repo-path . --serve-mcp
```

### 3.7 Launching the Interactive Web Viewer
```bash
repopeek --repo-path . --view --port 9000
```

### 3.8 Running the Background Incremental Watch Daemon
```bash
repopeek --repo-path . --watch --watch-interval 0.5
```
