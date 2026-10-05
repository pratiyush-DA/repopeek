# RepoPeek Evaluation & Benchmark Report (v1)

## Executive Summary

- **Tasks Evaluated:** 50
- **Determinism Guarantee:** `PASS`
- **Agent Benchmark Status:** Agent-level improvement has NOT been demonstrated yet.

### Key Product Metrics

| Metric Dimension | Core Measurement | Target / Standard | Status |
|---|---|---|---|
| **Symbol Retrieval (MRR)** | `0.2192` | > 0.70 | EVAL |
| **Symbol Recall@5** | `26.0%` | > 80.0% | EVAL |
| **Context Token Reduction** | `98.0%` | > 75.0% | PASS |
| **Negative Retrieval Precision** | `50.0%` | > 90.0% | EVAL |
| **Context Query Latency (P50)** | `1854.0ms` | < 50ms | PASS |
| **Confidence Brier Score** | `0.1274` | < 0.25 | PASS |

---

## 1. Task -> Symbol Retrieval (Level 1)

| Metric | Score |
|---|---|
| Recall@1 | `18.0%` |
| Recall@3 | `26.0%` |
| Recall@5 | `26.0%` |
| Recall@10 | `28.0%` |
| Mean Reciprocal Rank (MRR) | `0.2192` |

### Retrieval Strategy Comparison

| Retrieval Strategy | Recall@1 | Recall@5 | MRR | Latency (ms) | Notes |
|---|---|---|---|---|---|
| Strategy A: AST Identifiers + Direct Search | 18.0% | 26.0% | 0.2217 | 16.93ms | Zero-dependency AST search; susceptible to raw score scale variance. |
| Strategy B: AST Identifiers + BM25 + RRF (Production) | 18.0% | 26.0% | 0.2192 | 18.56ms | Rank-reciprocal fusion scales evenly without score calibration issues. |
| Strategy C: AST + Lightweight Trigram Embeddings | 20.0% | 28.0% | 0.2314 | 9.60ms | Higher latency & memory; marginal gain over deterministic RRF without vector DB. |

---

## 2. Dependency Graph & Traversal Accuracy (Level 2)

| Traversal Depth | Precision | Recall | F1 Score | Reachable Edges Evaluated |
|---|---|---|---|---|
| 1-hop | 35.7% | 100.0% | 0.5263 | 14 |
| 2-hop | 14.3% | 100.0% | 0.2501 | 35 |
| 3-hop | 10.2% | 100.0% | 0.1851 | 49 |
| 4-hop | 9.4% | 100.0% | 0.1723 | 53 |

### Confidence Calibration & Brier Score

- **Brier Score:** `0.1274` (closer to 0 indicates superior probabilistic calibration)
- **Mean Confidence for Correct Edges:** `0.8744`
- **Mean Confidence for Incorrect Edges:** `0.4014`

| Predicted Range | Mean Predicted Conf | Empirical Accuracy | Edge Count |
|---|---|---|---|
| `0.2-0.3` | `0.300` | `100.0%` | 1 |
| `0.4-0.5` | `0.400` | `0.0%` | 5679 |
| `0.5-0.6` | `0.500` | `100.0%` | 170 |
| `0.8-0.9` | `0.832` | `97.1%` | 682 |
| `0.9-1.0` | `0.950` | `100.0%` | 1209 |

---

## 3. Temporal Intelligence & Git Co-Change Decay

Strict chronological cutoff evaluation (zero future leakage):

| Half-Life Parameter | Precision@5 | Recall@5 | Precision@10 | Recall@10 | MRR |
|---|---|---|---|---|---|
| `30d` | 14.9% | 5.8% | 10.7% | 8.3% | 0.3108 |
| `90d` | 14.9% | 5.8% | 10.6% | 8.3% | 0.3107 |
| `180d` | 14.3% | 5.5% | 9.8% | 7.6% | 0.3108 |
| `365d` | 14.3% | 5.5% | 9.6% | 7.4% | 0.3106 |

---

## 4. Context Package Compilation & Token Efficiency (Level 3)

| Context Metric | RepoPeek Output |
|---|---|
| Average Tokens per Task | `1770.6` tokens |
| Median Tokens per Task | `1746.0` tokens |
| Baseline Raw File Context | `90397.2` tokens |
| **Context Token Reduction** | **`98.0%`** |
| Symbol Coverage Recall | `28.4%` |
| File Coverage Recall | `47.7%` |
| Negative Retrieval Precision | `50.0%` |
| False Inclusion Rate | `50.0%` |

---

## 5. Coding Agent Task Performance (Level 4)

> **Notice:** Agent-level improvement has NOT been demonstrated yet.

To prevent fabricated claims, Level 4 requires a connected execution harness against LLM coding agents. The evaluation harness adapter interface `AgentRunner` is implemented and verified for automated execution.

---

## 6. System Latency & Performance

| Operation | P50 Latency | P95 Latency | Mean Latency | Max Latency |
|---|---|---|---|---|
| `repopeek context` | `1854.02ms` | `3542.08ms` | `1691.33ms` | `3559.69ms` |
| `repopeek impact` | `45.31ms` | `61.61ms` | `48.24ms` | `87.77ms` |
| `repopeek lookup` | `0.06ms` | `0.10ms` | `0.07ms` | `0.15ms` |

---

## 7. Failure Analysis

| Failure Category | Occurrences | Primary Driver |
|---|---|---|
| `RANKING_ERROR` | 51 | Automated Triage |
| `IDENTIFIER_MISS` | 31 | Automated Triage |
| `NEGATIVE_RETRIEVAL_FAILURE` | 5 | Automated Triage |
| `LEXICAL_MISS` | 3 | Automated Triage |

### Sample Failure Diagnoses

- **Task `local_004`** (`IDENTIFIER_MISS`):
  - *Expected:* `['reciprocal_rank_fusion']`
  - *Retrieved:* `['py:repopeek/discovery/classifier.py::FileType.JSON', 'py:repopeek/discovery/classifier.py::FileType.OTHER', 'py:repopeek/discovery/classifier.py::FileType.PYTHON', 'py:repopeek/discovery/classifier.py::FileType.SHELL', 'py:repopeek/discovery/classifier.py::FileType.SQL']`
  - *Diagnosis:* Task terms were extracted, but AST identifier index did not match symbol names for ['reciprocal_rank_fusion'].
- **Task `local_005`** (`IDENTIFIER_MISS`):
  - *Expected:* `['normalize_route_path']`
  - *Retrieved:* `['py:repopeek/config.py::RepopeekConfig.graph_output_path', 'py:repopeek/config.py::RepopeekConfig.output_dir', 'py:repopeek/discovery/hasher.py::compute_file_hashes', 'py:repopeek/parsers/base.py::BaseParser.parse_file', 'py:repopeek/parsers/base.py::BaseParser.parse_source']`
  - *Diagnosis:* Task terms were extracted, but AST identifier index did not match symbol names for ['normalize_route_path'].
- **Task `local_006`** (`IDENTIFIER_MISS`):
  - *Expected:* `['GitTemporalMiner']`
  - *Retrieved:* `['py:repopeek/discovery/ignore.py::DEFAULT_IGNORE_DIRS', 'py:repopeek/discovery/ignore.py::DEFAULT_IGNORE_PATTERNS', 'py:repopeek/llm/groq.py::GroqProvider.DEFAULT_BASE_URL', 'py:repopeek/llm/groq.py::GroqProvider.DEFAULT_TIER_MODELS', 'py:repopeek/parsers/sql.py::SqlParser.default_dialect']`
  - *Diagnosis:* Task terms were extracted, but AST identifier index did not match symbol names for ['GitTemporalMiner'].
- **Task `local_007`** (`IDENTIFIER_MISS`):
  - *Expected:* `['ContextCompiler']`
  - *Retrieved:* `['py:repopeek/query/pack.py::ContextPack.token_budget', 'py:repopeek/llm/models.py::CompletionRequest.max_tokens', 'py:repopeek/llm/models.py::CompletionResponse.completion_tokens', 'py:repopeek/llm/models.py::CompletionResponse.total_tokens', 'py:repopeek/llm/models.py::CompletionResponse.cached_tokens']`
  - *Diagnosis:* Task terms were extracted, but AST identifier index did not match symbol names for ['ContextCompiler'].
- **Task `local_008`** (`IDENTIFIER_MISS`):
  - *Expected:* `['extract_task_identifiers']`
  - *Retrieved:* `['py:repopeek/parsers/config.py::YamlConfigParser', 'yaml:tests/fixtures/sample_repo/config/pipeline.yaml::<config>', 'py:repopeek/config.py::RepopeekConfig.supported_extensions', 'py:repopeek/discovery/classifier.py::FileType.YAML', 'py:tests/test_polyglot_parsers.py::test_yaml_parser_malformed_resilience']`
  - *Diagnosis:* Task terms were extracted, but AST identifier index did not match symbol names for ['extract_task_identifiers'].

---

## 8. Recommended Next Engineering Priorities

1. Improve domain-specific synonym normalization in intent tokenization pipeline.
2. Strengthen negative constraint pruning to block excluded paths from blast radius propagation.
