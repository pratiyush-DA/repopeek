# Component: Git Temporal Miner & Co-Change Matrix

## 1. Overview
The temporal mining subsystem analyzes historical git commit activity to discover hidden architectural dependencies between files that frequently change together, even when no static syntactic link (e.g. import or function call) connects them.

- **Package:** `repopeek.temporal`
- **Source File:** [`repopeek/temporal/miner.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/repopeek/temporal/miner.py)
- **Primary Tests:**
  - [`tests/test_temporal_cochange.py`](file:///c:/Users/pkumar2/OneDrive%20-%20Data%20Axle/Documents/AI_INIT/Repopeek/tests/test_temporal_cochange.py)

---

## 2. Commit Mining Architecture

### Execution (`mine_commits`)
1. Runs `git log --no-merges --name-only --format=COMMIT:%H|%at -n2000` via `subprocess.run()`.
2. Parses commit SHA, Unix timestamp, and the set of modified repository-relative file paths.
3. **Commit Filtering:**
   - Skips commits with $< 2$ files (no co-change possible).
   - Skips commits with $> 50$ files (`max_files_per_commit` default 50). Mass refactorings, repository formatting, and dependency lock updates skew co-change statistics and are filtered out as noise.

---

## 3. Mathematical Half-Life Time Decay

Co-change evidence is weighted using exponential decay so recent commits have significantly greater influence than multi-year-old changes:

### Decay Constant
$$\lambda = \frac{\ln(2)}{t_{1/2}} \quad \text{where } t_{1/2} = 180\text{ days (default)}$$

### Commit Weight
For commit $c$ with timestamp $t_c$ relative to reference timestamp $t_{\text{ref}}$ (HEAD commit time):

$$w_c = \exp\left(-\lambda \cdot (t_{\text{ref}} - t_c)\right)$$

### Conditional Co-Change Probability $P(B \mid A)$
For file pair $(A, B)$, the probability that changing file $A$ requires modifying file $B$ is:

$$P(B \mid A) = \frac{\sum_{c \in C_{A \cap B}} w_c}{\sum_{c \in C_A} w_c}$$

---

## 4. Graph Edge Synthesis (`build_graph_edges`)

1. Pairs with $P(B \mid A) \ge \text{min\_confidence}$ (default 0.25) and $\text{co\_commit\_count} \ge \text{min\_commits}$ (default 2) are materialized.
2. Creates directed `Edge`:
   - `src`: Root file node ID for file $A$.
   - `dst`: Root file node ID for file $B$.
   - `type`: `EdgeType.CO_CHANGED_WITH`.
   - `confidence`: `Confidence.RESOLVED`.
   - `evidence`: `Evidence(how_derived="git_temporal_cochange(P=0.85, commits=12)")`.

These edges enter the canonical graph and are automatically traversed during blast radius analysis, alerting developers and agents when touching a model requires updating an unimported configuration or migration script.
