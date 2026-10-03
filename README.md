# RepoPeek — Multi-Agent Code Intelligence Engine

RepoPeek is a lightweight, local Semantic Code Property Graph (SCPG) engine designed to index any repository down to atomic units and materialize task-specific lenses and budget-governed context packs for low-context (<500 tokens) AI coding agents.

---

## Key Capabilities

- **Polyglot Parsing Substrate**: High-fidelity syntactic extraction across Python (stdlib AST), SQL (SQLGlot AST with multi-dialect support), Shell (shlex command & argument tokenization), JSON, and YAML keypaths.
- **Cross-Language Bridges & Data Flow**: Automatically tracks variable def-use flows (`READS`, `WRITES`), subprocess invocations, SQL table bindings, and configuration dependencies across language boundaries.
- **Deterministic Lens Materialization**: Computes 9 focused graph projections on demand:
  `Module`, `Symbol`, `Call`, `Class`, `Data`, `Entity`, `Config`, `Process`, and `Exception`.
- **Git Provenance & Content-Addressed Sharding**: Binds every node and edge to exact file spans, git commit SHAs, repository dirty states, and content blob hashes with atomic JSON sharding and a high-speed SQLite recursive CTE cache.
- **5-Tier Story Cascade & Anti-Hallucination Guardrails**:
  1. *Tier 1*: Deterministic AST fact templates (zero cost).
  2. *Tier 2*: SHA-256 content-hash story cache with disk persistence.
  3. *Tier 3*: Cheap-model structured summaries (Groq `llama-3.1-8b-instant`).
  4. *Tier 4*: Bottom-up hierarchical aggregation.
  5. *Tier 5*: Fact Verifier validating generated claims against AST reality (`calls`, `reads`, `writes`, `raises`) with automatic fallback.
- **Low-Context Retrieval Engine**: Answers blast radius and flow queries instantly:
  - `lookup`: Exact symbol or identifier retrieval.
  - `neighbors`: 1-hop inbound and outbound relationship inspection.
  - `impact`: Bidirectional upstream and downstream blast-radius reachability analysis.
  - `data_trace`: Traces who writes and who reads any table or variable entity.
  - `context_pack`: Compact, budget-governed markdown context pack (<500 tokens) ready for LLM consumption.
- **Stdio JSON-RPC MCP Server**: Standard Model Context Protocol server exposing tool capabilities directly to AI IDEs (Antigravity, Cursor, Claude Desktop).

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
# Deterministic offline indexing (zero LLM calls, instant)
python -m repopeek.cli --repo-path /path/to/target-repo --offline

# Cost estimation dry-run
python -m repopeek.cli --repo-path /path/to/target-repo --dry-run

# Full indexing with Groq LLM enrichment (reads GROQ_API_KEY from .env)
python -m repopeek.cli --repo-path /path/to/target-repo
```

### 3. Querying the Code Graph

```bash
# Look up an atomic node card
python -m repopeek.cli --lookup InvoiceParser.parse

# Compute blast radius ("If I change X, what breaks?")
python -m repopeek.cli --impact InvoiceParser.parse

# Trace data flow for an entity or SQL table ("Who writes X? Who reads X?")
python -m repopeek.cli --trace table.invoices

# Generate a budget-governed context pack (<500 tokens)
python -m repopeek.cli --pack InvoiceParser.parse
```

### 4. Serve MCP (Model Context Protocol)

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
| `repopeek_impact` | `target_query` (str), `max_depth` (int), `direction` (str) | Calculate complete blast radius tree (affected files, tables, and callers). |
| `repopeek_data_trace` | `entity_query` (str) | Trace definitions, writes, reads, and downstream dependencies. |
| `repopeek_context_pack` | `target_queries` (list[str]), `token_budget` (int) | Generate formatted markdown context pack fitting strictly within token budget. |

---

## Golden Scenarios Validation

RepoPeek's retrieval engine has been verified against 3 core golden test scenarios (`tests/test_golden_scenarios.py`):

1. **Question 1: Blast Radius**
   - *Target:* `InvoiceParser.parse` & `table.invoices`
   - *Result:* Traced across Python orchestrator, SQL queries, shell dispatch scripts, and YAML configuration. Identified exact affected files and database tables.
2. **Question 2: Data Flow Traceability**
   - *Target:* `table.invoices` & `database.dialect`
   - *Result:* Accurately separated writer nodes (`WRITES` from SQL `INSERT INTO invoices`) and reader nodes (`READS` from SQL `SELECT ... FROM invoices`).
3. **Question 3: Sub-500 Token Context Pack**
   - *Target:* `InvoiceParser.parse`
   - *Result:* Materialized atomic node cards, signatures, and blast radius summaries within ~198 tokens, providing complete context for an autonomous agent without reading the repository.

---

## Architecture & Conventions

- **Decision Ladder (Ponytail Protocol: `full`)**: YAGNI -> Existing codebase -> Stdlib -> Existing dependencies -> Smallest correct implementation.
- **Knowledge Vault**: All architectural decisions, schemas, and operational logs are strictly maintained in `knowledge_vault/` and validated via `python knowledge_vault/_meta/validate.py`.
- **License**: MIT
