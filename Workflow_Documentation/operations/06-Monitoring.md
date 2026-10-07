# Monitoring, Observability, and Metrics

This document describes the observability features, logging configurations, token accounting, and performance metrics provided by RepoPeek.

---

## 1. Logging and Verbosity

RepoPeek uses Python's standard library `logging` framework. Logs are formatted without decorative emojis to maintain clean parsing in CI pipelines and automated agent wrappers.

### Log Levels
- `DEBUG`: Fine-grained AST tokenization events, individual edge resolutions, SQLite queries, and cache hits/misses.
- `INFO`: Lifecycle milestones (crawling completed, parser dispatch stats, lens materialization, export timing).
- `WARNING`: Recoverable syntax errors in parsed source files, unresolvable import targets, fallback heuristic parser activations.
- `ERROR`: Fatal I/O failures, corrupted JSON graphs, or unhandled exceptions.

### Controlling Verbosity
Set via environment variable:
```bash
# Enable verbose debug logs
export REPOPEEK_LOG_LEVEL=DEBUG

# Restrict to warnings and errors
export REPOPEEK_LOG_LEVEL=WARNING
```

---

## 2. Integrity and Health Metrics (`manifest.json`)

Every indexing run records runtime metrics into `.repopeek/manifest.json`:

```json
{
  "schema_version": "1.0.0",
  "tool_version": "0.1.0",
  "repo_commit": "e5b8d2...",
  "dirty": false,
  "nodes_count": 1420,
  "edges_count": 3890,
  "graph_sha256": "3a88c...",
  "lenses": { ... },
  "shards": { ... }
}
```

### Health Check Thresholds:
- **Zero Nodes / Edges:** Indicates either an invalid `--repo-path`, over-aggressive exclusion filters, or unparseable source files.
- **SHA-256 Stability:** If code has not changed between commits, `graph_sha256` must remain byte-for-byte identical.
- **Orphan Edge Ratio:** High counts of unresolved edges indicate missing standard library definitions or unmapped cross-file exports.

---

## 3. Token Accounting and Cost Estimation

When using LLM-powered semantic story generation, RepoPeek provides pre-execution token accounting to avoid surprise costs:

### Running a Dry-Run Estimation
```bash
repopeek --repo-path . --dry-run
```

### Output Breakdown
```text
=== RepoPeek LLM Cost Estimation ===
Candidate Nodes for Enrichment: 342
Estimated Prompt Tokens:        171,000 (avg 500 tokens/node)
Estimated Completion Tokens:    34,200  (avg 100 tokens/node)
Target Model:                   qwen/qwen3.8-27b (Groq Cloud)
Estimated Cost:                 ~$0.04 USD
Estimated Latency:              ~18.5 seconds (at 50 req/sec rate limit)
```

---

## 4. Evaluation and Benchmarking Metrics

Invoked via `repopeek --evaluate --dataset benchmarks/v1/tasks.yaml`, the evaluation engine outputs formal machine-readable performance metrics:

### 4.1 Retrieval Quality Metrics
- **Mean Reciprocal Rank (MRR):**
  $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
  Measures how high the true ground-truth seed appears in candidate rankings. Target: $\ge 0.85$.
- **Recall@K:** Fraction of required ground-truth modification targets captured in the top $K$ retrieved symbols. Target: Recall@5 $\ge 0.90$.

### 4.2 Blast Radius Calibration (Brier Score)
Evaluates whether predicted failure probabilities $p_i$ match real-world propagation rates:
$$\text{BS} = \frac{1}{N} \sum_{i=1}^N (p_i - o_i)^2$$
Where $o_i \in \{0, 1\}$ represents whether node $i$ was actually modified in a historical co-change commit. Target: $\text{BS} \le 0.15$.

---

## 5. Performance Profiling

To profile indexing bottlenecks:

```bash
# CPU Execution Profile
python -m cProfile -o repopeek.prof -m repopeek.cli --repo-path . --output-dir .repopeek --offline

# Inspect Top 20 Time-Consuming Functions
python -c "import pstats; p = pstats.Stats('repopeek.prof'); p.sort_stats('cumulative').print_stats(20)"
```
