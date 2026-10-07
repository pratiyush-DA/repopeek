# Component: Hybrid Retrieval & Intent Engine

## 1. Overview
The retrieval subsystem maps natural language engineering tasks into concrete, ranked candidate code symbols completely offline without requiring vector databases, embedding models, or GPU acceleration.

- **Package:** `repopeek.retrieval`
- **Source File:** [`repopeek/retrieval/intent.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/retrieval/intent.py)
- **Primary Tests:**
  - [`tests/test_retrieval.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_retrieval.py)
  - [`tests/test_retrieval_reliability.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_retrieval_reliability.py)

---

## 2. Intent Normalization Pipeline

When a natural language prompt is supplied, `extract_task_identifiers()` executes a multi-stage normalization:

```text
User Prompt: "Fix ParseError in InvoiceParser.parse without modifying shipping"
    │
    ├── 1. Code Identifier Extraction:
    │      Regex matching captures: ["InvoiceParser.parse", "ParseError"]
    │
    ├── 2. Stop Word & Operational Verb Filtering:
    │      Strips: "in", "without", "modifying"
    │      Filters operational verbs: "fix"
    │      Retains technical verbs: "parse"
    │
    ├── 3. Linguistic Stemming:
    │      "invoices" -> "invoic"
    │      "parsers" -> "parser"
    │      "parsing" -> "pars"
    │
    ├── 4. Compound Bigram Generation:
    │      ["invoice_parser", "parser_parse"]
    │
    └── 5. Negative Constraint Extraction:
           Captures exclusion: ["shipping"]
```

---

## 3. Calibrated Multi-Component Scoring

Candidate symbols are scored using six normalized dimensions:

$$\text{RetrievalScore}(S) = 0.35 \cdot E + 0.25 \cdot I + 0.20 \cdot T + 0.10 \cdot L + 0.05 \cdot P + 0.05 \cdot K$$

| Component | Weight | Calculation Method |
|---|---|---|
| **$E$ (Exact Match)** | 0.35 | 1.0 if symbol ID, qualified name, or bare name exactly matches query identifier; 0.0 otherwise. |
| **$I$ (Identifier Match)** | 0.25 | Proportion of extracted code identifiers or camelCase/snake_case tokens matching the symbol. |
| **$T$ (Token Overlap)** | 0.20 | Jaccard overlap between query concept terms and the symbol's name, signature, and story narrative. |
| **$L$ (Lexical BM25)** | 0.10 | Normalized BM25 score from the SQLite FTS5 `nodes_fts` table. |
| **$P$ (Path Relevance)** | 0.05 | Overlap between file paths mentioned in query and the node's source file span. |
| **$K$ (Kind Preference)** | 0.05 | Prioritizes actionable code: functions/methods = 1.0, classes = 0.9, files = 0.5, variables = 0.3. |

### Reciprocal Rank Fusion (RRF)
When combining disjoint candidate lists without score calibration, `reciprocal_rank_fusion()` ranks candidates via:

$$\text{RRFScore}(d) = \sum_{m \in M} \frac{1}{60 + r_m(d)}$$

---

## 4. Deterministic Explain Mode (`--explain`)

RepoPeek provides a full diagnostic explain report for any query via `python -m repopeek.cli --explain "<query>"`:

```text
Query: 'Change invoice validation in InvoiceParser.parse'
Extracted Identifiers: ['InvoiceParser.parse']
Extracted Concepts: ['invoice', 'validation', 'parser', 'parse']
Extracted Stems: ['invoic', 'valid', 'parser', 'pars']

Top Candidates:
1. py:src/billing/invoice.py::InvoiceParser.parse (Score: 0.8850)
   - exact_match: 1.0000 (wt: 0.3500)
   - identifier: 1.0000 (wt: 0.2500)
   - token_overlap: 0.6000 (wt: 0.1200)
   - lexical: 0.9000 (wt: 0.0900)
   - path_relevance: 0.5000 (wt: 0.0250)
   - kind_preference: 1.0000 (wt: 0.0500)
```
