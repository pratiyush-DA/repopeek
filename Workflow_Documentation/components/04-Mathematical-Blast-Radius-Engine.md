# Component: Mathematical Blast Radius Engine

## 1. Overview
The blast radius engine calculates evidence-backed, multi-hop reachability trees answering the core question: *"If I change symbol X, what downstream callers, database tables, and configuration files break?"*

Unlike naive graph search that floods entire codebases, RepoPeek applies exponential path decay, multi-path noisy-or combination, distance discounting, and hard exclusion pruning.

- **Package:** `repopeek.graph`
- **Source File:** [`repopeek/graph/blast_radius.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/graph/blast_radius.py)
- **Primary Tests:** [`tests/test_blast_radius.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_blast_radius.py).

---

## 2. Mathematical Traversal Formulation

### Path Confidence with Distance Decay
For a traversal path $P = (e_1, e_2, \dots, e_h)$ consisting of $h$ relational hops, each with prior confidence $c_i$:

$$\text{PathConfidence}(P) = \min\left(0.99, \prod_{i=1}^{h} c_i \cdot \exp\left(-0.25 \cdot (h - 1)\right)\right)$$

- **Decay Factor:** $-0.25$ per additional hop reflects diminishing certainty as changes propagate through indirect dependencies.
- **Max Confidence Cap:** 0.99 (avoids false certainty).

### Multi-Path Combination (Noisy-OR)
If a node $N$ can be reached through multiple independent paths $\{P_1, P_2, \dots, P_k\}$:

$$\text{CombinedConfidence}(N) = \min\left(0.99, 1 - \prod_{j=1}^{k} \left(1 - \text{PathConfidence}(P_j)\right)\right)$$

*Example:* If a caller is reachable through two separate 2-hop paths each with confidence 0.60, the combined confidence is:
$$1 - (1 - 0.60)(1 - 0.60) = 1 - 0.16 = 0.84$$

### Distance-Decayed Graph Score
Used by retrieval and context compilation to rank node relevance:

$$\text{GraphScore}(N) = \text{CombinedConfidence}(N) \cdot \exp\left(-0.70 \cdot (\text{distance} - 1)\right)$$

---

## 3. Blast Radius Partitioning

| Partition | Inclusion Criteria | Role in Context Package |
|---|---|---|
| **Direct** | $\text{distance} = 1$ OR $\text{CombinedConfidence}(N) \ge 0.80$ | Immediate callers, direct callees, and mandatory migration targets. Included in Level 1, 2, and 3 packages. |
| **Indirect** | $\text{CombinedConfidence}(N) \ge 0.20$ AND not direct | Secondary affected files and upstream consumers. Included in Level 2 and 3 packages subject to token budget. |
| **Excluded** | $\text{CombinedConfidence}(N) < 0.20$ OR $\text{depth} > \text{max\_depth}$ OR matches explicit exclusion rule | Pruned from context to save tokens and prevent agent hallucinations. |

---

## 4. Hard Negative Exclusion Pruning

`is_node_excluded(node_id, node_card, exclusions)` evaluates explicit negative constraints passed in queries or task prompts (e.g. `without modifying shipping`).

Supported exclusion patterns:
- **Directory patterns:** `shipping/`, `tests/shipping/`, `scripts/`
- **File patterns:** `shipping.py`, `shipping/service.py`, `db/queries.sql`
- **Symbol patterns:** `ShippingService`, `parse_shipping`, exact `node_id`
- **Glob patterns:** `**/shipping/**`, `*shipping*`, `tests/*`

**Pruning Mechanism:**
Exclusion is evaluated **before** pushing nodes into the BFS queue. When a node matches an exclusion rule:
1. It is recorded as an `ExcludedNode(exclusion_reason="Explicit negative exclusion rule matched")`.
2. It is **never** expanded, terminating graph traversal along that branch.
3. This prevents excluded modules from acting as transit hubs into other components.

---

## 5. Blast Radius Data Structures

- `BlastRadiusStep`: Captures `src`, `dst`, `type`, `confidence`, `flow` (`upstream` / `downstream`), `citation` (e.g. `invoice.py:15-30`), and `how_derived`.
- `BlastRadiusPath`: Captures the sequence of steps and resulting `path_confidence`.
- `AffectedNode`: Captures `node_id`, `kind`, `file`, `citation`, `distance`, `combined_confidence`, `graph_score`, `category` (`direct` / `indirect`), and contributing paths.
- `ExcludedNode`: Captures `node_id`, `distance`, `confidence`, and `exclusion_reason`.
- `BlastRadiusReport`: Complete evidence report containing partitioned lists, `affected_files`, `affected_tables`, `affected_configs`, traversed edges, and diagnostic metrics.
