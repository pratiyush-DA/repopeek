# RepoPeek — Multi-Agent Code Intelligence Engine

RepoPeek is a lightweight, local Semantic Code Property Graph (SCPG) engine. It indexes a repository into a queryable graph and compiles **task-specific packs of ≤4 files with ~40-line spans** (~1–2k tokens) for AI coding agents.

It is the **primary navigation map**, not a closed-world dump of the repo. Agents should trust `compile_context` / `resolve` / `lookup`, then open the listed files.

**Handoff for new agents:** [Workflow_Documentation/07-Agent-Handoff.md](Workflow_Documentation/07-Agent-Handoff.md).

---

## Key Capabilities

- **Polyglot Parsing Substrate**: Python (stdlib AST), TypeScript/JavaScript, SQL (SQLGlot; postgres detect when `postgres/` exists), Shell, JSON, YAML.
- **Cross-Language Bridges & Data Flow**: Automatically tracks variable def-use flows (`READS`, `WRITES`), subprocess invocations, SQL table bindings, and configuration dependencies across language boundaries.
- **Deterministic Lens Materialization**: Computes 9 focused graph projections on demand:
  `Module`, `Symbol`, `Call`, `Class`, `Data`, `Entity`, `Config`, `Process`, and `Exception`.
- **Git Provenance & Content-Addressed Sharding**: Binds every node and edge to exact file spans, git commit SHAs, repository dirty states, and content blob hashes with atomic JSON sharding and a high-speed SQLite recursive CTE cache.
- **5-Tier Story Cascade & Anti-Hallucination Guardrails**:
  1. *Tier 1*: Deterministic AST fact templates (zero cost).
  2. *Tier 2*: SHA-256 content-hash story cache with disk persistence.
  3. *Tier 3*: Cheap-model structured summaries (Groq `qwen/qwen3.8-27b` by default; strong tier `openai/gpt-oss-120b`).
  4. *Tier 4*: Bottom-up hierarchical aggregation.
  5. *Tier 5*: Fact Verifier validating generated claims against AST reality (`calls`, `reads`, `writes`, `raises`) with automatic fallback.
- **Low-Context Retrieval Engine**: Answers blast radius and flow queries instantly:
  - `lookup`: Exact symbol or identifier retrieval.
  - `neighbors`: 1-hop inbound and outbound relationship inspection.
  - `impact`: Bidirectional upstream and downstream blast-radius reachability analysis.
  - `data_trace`: Traces who writes and who reads any table or variable entity.
  - `context_pack`: Compact pack for known symbol ids.
  - `compile_context` / `repopeek_context`: NL task → ≤4 files, exclusions, snippets, `coverage`.
- **Stdio JSON-RPC MCP Server**: Standard Model Context Protocol server exposing **10 tools** directly to AI IDEs (Antigravity, Cursor, Claude Desktop).

---

## Quickstart & CLI Usage

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/pratiyush-DA/repopeek.git
cd repopeek

# Install dependencies in a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Index a Repository

```bash
# Deterministic offline indexing (zero LLM). Abort if >400 files or >8000 nodes.
python -m repopeek --repo-path /path/to/target-repo --output-dir ./output --offline

# Groq overlay (GROQ_API_KEY required; optional GROQ_API_KEY_2 / GROQ_API_KEY_3)
# REPOPEEK_LLM_MAX_NODES=200 REPOPEEK_LLM_CONCURRENCY=2
python -m repopeek --repo-path /path/to/target-repo --output-dir ./output
```

### 3. Querying the Code Graph

```bash
# Look up an atomic node card
python -m repopeek.cli --lookup InvoiceParser.parse

# Compute blast radius ("If I change X, what breaks?")
python -m repopeek.cli --impact InvoiceParser.parse

# Trace data flow for an entity or SQL table ("Who writes X? Who reads X?")
python -m repopeek.cli --trace table.invoices

# Generate a budget-governed context pack
python -m repopeek --pack InvoiceParser.parse --output-dir ./output

# Compile a natural-language task (preferred for agents)
python -m repopeek --context "Raise MAX_LLM_RETRIES in metadata generation" --output-dir ./output
```

### 4. Interactive Web Graph Viewer (Obsidian-Style)

Launch a local, zero-dependency force-directed code property graph viewer in your default browser:

```bash
python -m repopeek.cli --view
# Custom port:
python -m repopeek.cli --view --port 9000
```
- **Capabilities:** 9 switchable lenses (`Call Graph`, `Module Hierarchy`, `Data Flow`, etc.), interactive zoom/pan, hover glowing links, real-time symbol search, click-to-inspect node drawer, and one-click blast radius highlighting.

### 5. Export to Obsidian Vault

Export the code property graph as a structured, native Obsidian Markdown vault complete with `.obsidian/` color groups and bidirectional `[[wikilinks]]`:

```bash
# Export graph to an Obsidian vault
python -m repopeek.cli --export-obsidian ./my_obsidian_vault

# Query documentation note directly from the Obsidian vault
python -m repopeek.cli --read-obsidian GraphQueryEngine --vault-path ./my_obsidian_vault
```
Open `./my_obsidian_vault` in **Obsidian Desktop** to explore your codebase using Obsidian's native force-directed **Graph View**!

### 6. Serve MCP (Model Context Protocol)

```bash
python -m repopeek.cli --serve-mcp
```

---

## MCP Server Configuration

To connect RepoPeek to AI coding agents, add the server configuration to your tool's MCP configuration file (e.g. `mcp_config.json` or `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "repopeek": {
      "command": "python",
      "args": [
        "-m",
        "repopeek.cli",
        "--repo-path",
        "/absolute/path/to/target-repo",
        "--serve-mcp"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### Available MCP Tools

| Tool | Parameters | Description |
|---|---|---|
| `repopeek_lookup` | `query` (str) | Search and retrieve atomic node card by symbol name or node ID. |
| `repopeek_neighbors` | `query` (str) | Inspect direct incoming and outgoing graph edges. |
| `repopeek_impact` | `target` (str), `max_depth` (int), `direction` (str) | Calculate complete blast radius tree (affected files, tables, and callers). |
| `repopeek_data_trace` | `query` (str) | Trace definitions, writes, reads, and downstream dependencies. |
| `repopeek_context_pack` | `targets` (list[str]), `token_budget` (int) | Generate formatted markdown context pack fitting strictly within token budget. |
| `repopeek_context` | `task` (str), `budget` (int), `level` (int) | Compile a task-aware context package with blast radius and constraints. |
| `repopeek_plan` | `task` (str) | Generate a risk-assessed step-by-step change plan. |
| `repopeek_routes` | | List detected HTTP client calls and server routes. |
| `repopeek_co_changes` | `target` (str) | Show temporally coupled files from git co-change mining. |
| `repopeek_resolve` | `task` (str) | Rank symbol candidates for a natural-language engineering task. |

---

## Golden Scenarios Validation

RepoPeek's retrieval engine has been verified against 3 core golden test scenarios (`tests/test_golden_scenarios.py`):

1. **Question 1: Blast Radius**
   - *Target:* `InvoiceParser.parse` & `table.invoices`
   - *Result:* Traced across Python orchestrator, SQL queries, shell dispatch scripts, and YAML configuration. Identified exact affected files and database tables.
2. **Question 2: Data Flow Traceability**
   - *Target:* `table.invoices` & `database.dialect`
   - *Result:* Accurately separated writer nodes (`WRITES` from SQL `INSERT INTO invoices`) and reader nodes (`READS` from SQL `SELECT ... FROM invoices`).
3. **Question 3: Context pack**
   - *Target:* `InvoiceParser.parse`
   - *Result:* Atomic cards and blast summaries in a small pack. Task-level `compile_context` now uses a **4-file cap** and ~40-line snippets (~1–2k tokens), not a sub-500-token whole-task dump.

---

## Testing

Always target `tests/` (never bare `pytest`; `testing/` is gitignored eval data and will collect foreign Django tests):

```bash
# Windows PowerShell
$env:PYTHONPATH="."
.venv\Scripts\python -m pytest tests
python knowledge_vault/_meta/validate.py
```

Dais real-world eval (gitignored): `testing/dais/run_mcp_matrix.py` after indexing into `testing/dais/repopeek`. See `Workflow_Documentation/operations/03-Testing.md`.

---

## Architecture & Conventions

- **Decision Ladder (Ponytail Protocol: `full`)**: YAGNI -> Existing codebase -> Stdlib -> Existing dependencies -> Smallest correct implementation.
- **Knowledge Vault**: requirements and schemas in `knowledge_vault/` (`python knowledge_vault/_meta/validate.py`).
- **Workflow docs**: `Workflow_Documentation/00-README.md`. Agent takeover: `Workflow_Documentation/07-Agent-Handoff.md`.
- **License**: MIT
