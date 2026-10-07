# Configuration Flow & Options

This document defines the configuration hierarchy, precedence rules, schema options, and environment variables governing RepoPeek.

---

## 1. Configuration Precedence

Configuration settings are loaded in strict order of precedence:

```text
[Highest Priority]
1. Explicit CLI Arguments (e.g. --repo-path, --output-dir, --sql-dialect, --budget)
       │
       ▼
2. JSON Configuration File (passed via --config <path>)
       │
       ▼
3. Environment Variables (.env file or OS environment)
       │
       ▼
4. Default RepopeekConfig Values in code
[Lowest Priority]
```

---

## 2. Configuration Schema (`RepopeekConfig`)

Defined in [`repopeek/config.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/config.py):

| Field Name | Type | Default Value | Description |
|---|---|---|---|
| `repo_path` | `Path` | `Path(".")` | Root filesystem path of the repository being analyzed. |
| `supported_extensions` | `List[str]` | `[".py", ".sql", ".sh", ".bash", ".json", ".yaml", ".yml"]` | Default file extensions recognized by config model (Note: Discovery scanner also supports `.ts`, `.tsx`, `.js`, etc.). |
| `output_dir` | `Path` | `Path("./output")` | Directory where generated property graphs, shards, lenses, and caches are written. |
| `graph_filename` | `str` | `"graph.json"` | Name of the primary canonical property graph file. |
| `sql_dialect` | `str` | `"oracle"` | Default SQL dialect for SQLGlot parser (`oracle`, `postgres`, `ansi`, `snowflake`). |
| `max_file_size_kb` | `int` | `2048` | Maximum file size in KB to parse deterministically (files above this cap are skipped). |
| `log_level` | `str` | `"INFO"` | Logging verbosity level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

### Helper Property
- `graph_output_path`: Returns `output_dir / graph_filename` (e.g. `./output/graph.json`).

---

## 3. Environment Variables Reference

RepoPeek uses a lightweight environment loader ([`repopeek/llm/env.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/llm/env.py)) that inspects `.env` in the current working directory without external third-party packages:

| Environment Variable | Subsystem | Default Value | Description |
|---|---|---|---|
| `GROQ_API_KEY` | `repopeek.llm` | None | API key for Groq Cloud chat completions. If absent and `--offline` is not passed, falls back to deterministic provider. |
| `REPOPEEK_LLM_PROVIDER` | `repopeek.llm` | `"groq"` (if key exists) else `"fallback"` | Explicitly selects provider: `groq`, `mock`, `fallback`. |
| `GROQ_BASE_URL` | `repopeek.llm` | `https://api.groq.com/openai/v1` | Custom endpoint for Groq OpenAI-compatible completions API. |
| `GROQ_MODEL_FAST` | `repopeek.llm` | `"qwen/qwen3.8-27b"` | Model used for low-complexity node summaries. |
| `GROQ_MODEL_BALANCED`| `repopeek.llm` | `"qwen/qwen3.8-27b"` | Balanced tier model. |
| `GROQ_MODEL_STRONG` | `repopeek.llm` | `"openai/gpt-oss-120b"` | Model used for high-complexity nodes ($\text{complexity} \ge 10$) and hierarchical aggregations. |
| `PYTHONUNBUFFERED` | Runtime | None | Set to `1` when running MCP server over stdio to prevent pipe buffering. |

---

## 4. Example Configuration File

```json
{
  "repo_path": "/var/projects/my-service",
  "output_dir": "/var/projects/my-service/.repopeek",
  "graph_filename": "graph.json",
  "sql_dialect": "postgres",
  "max_file_size_kb": 1024,
  "log_level": "DEBUG"
}
```

Usage:
```bash
python -m repopeek.cli --config ./repopeek-config.json
```
CLI arguments passed alongside `--config` will override values specified within the JSON file.
