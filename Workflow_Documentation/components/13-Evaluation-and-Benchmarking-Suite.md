# Component: Evaluation & Benchmarking Suite

## 1. Overview
The evaluation subsystem provides rigorous, reproducible quality validation across all four layers of RepoPeek. It measures symbol retrieval ranking accuracy, graph traversal precision, confidence calibration, temporal co-change decay, and token reduction against verified ground truth task datasets.

- **Package:** `repopeek.evaluation`
- **Source Files:**
  - [`repopeek/evaluation/benchmark.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/evaluation/benchmark.py)
  - [`repopeek/evaluation/dataset.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/evaluation/dataset.py)
  - [`repopeek/evaluation/models.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/evaluation/models.py)
  - [`repopeek/evaluation/retrieval.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/evaluation/retrieval.py)
  - [`repopeek/evaluation/graph.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/evaluation/graph.py)
  - [`repopeek/evaluation/context.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/evaluation/context.py)
  - [`repopeek/evaluation/temporal.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/evaluation/temporal.py)
  - [`repopeek/evaluation/report.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/evaluation/report.py)
  - [`benchmarks/v1/tasks.yaml`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/benchmarks/v1/tasks.yaml)
- **Primary Tests:** [`tests/test_evaluation.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_evaluation.py).

---

## 2. Evaluation Levels and Metrics

### Level 1: Symbol Retrieval Accuracy
- **Candidate Recall@50, Recall@100:** Ensures target symbol is retrieved into initial candidate pool.
- **Recall@1, Recall@3, Recall@5, Recall@10:** Measures whether target symbols appear in top ranking positions.
- **Mean Reciprocal Rank (MRR):**
  $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
- **Ablation Configurations:** Evaluates baseline BM25 vs +Stemming vs +Compound Bigrams.
- **Strategy Comparison:** Evaluates AST search vs BM25+RRF vs Trigram embeddings.

### Level 2: Graph Accuracy & Probabilistic Calibration
- **Precision, Recall, F1:** Evaluated across multi-hop reachability paths (1-hop through 4-hop).
- **Brier Score:** Evaluates whether edge confidence scores represent genuine probabilities:
  $$\text{Brier} = \frac{1}{N} \sum_{i=1}^{N} (f_i - o_i)^2 \quad (\text{Target} < 0.25)$$
- **Expected Calibration Error (ECE):** Partitions predictions into 10 confidence bins and computes weighted deviation from empirical correctness.

### Temporal Intelligence
- **Chronological Cutoff Evaluation:** Strictly mines commits prior to target commit to eliminate future data leakage.
- Measures Precision@k, Recall@k, and MRR for co-change predictions across half-life parameters ($t_{1/2} \in \{30, 90, 180, 365\}\text{ days}$).

### Level 3: Context Compilation & Token Efficiency
- **Token Reduction Percentage:**
  $$\text{Reduction} = 100 \times \left(1 - \frac{\text{ContextPackage Tokens}}{\text{Raw File Tokens}}\right)$$
  Typically achieves **98.7%** reduction.
- **Negative Precision & Recall:** Evaluates whether excluded files/symbols are strictly kept out of context packages.
- **Determinism Check:** Compiles identical tasks multiple times to verify exact string equality across runs.

### Level 4: Agent Benchmark Harness
- **`AgentRunner`:** Abstract interface for running controlled agent experiments.
- **`MockAgentRunner`:** Deterministic mock simulating assisted vs unassisted agent metrics (tool calls, token consumption, regressions) for pipeline verification.
- **Real-World Harness:** Evaluated against `testing/da-assistant/` across 12 tasks (`tasks.yaml`, `run_experiment.py`, `FINAL-REPORT.md`).

---

## 3. Reporting and Automated Recommendations

`BenchmarkRunner.run_all()` synthesizes results into:
1. `benchmark-results.json`: Machine-readable summary for CI regression tracking.
2. `benchmark-report.md`: Human-readable markdown report with executive summaries and ablation tables.
3. Automated Recommendations: Maps detected `FailureCategory` counts directly to architectural improvements (e.g. `GRAPH_MISSING_EDGE` -> expand AST extraction; `LEXICAL_MISS` -> improve synonym normalization; `NEGATIVE_RETRIEVAL_FAILURE` -> strengthen exclusion pruning).
