"""Temporal intelligence evaluation with strict chronological cutoff to prevent future leakage."""

from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Set, Tuple

from repopeek.evaluation.metrics import precision_recall_f1, recall_at_k, reciprocal_rank
from repopeek.evaluation.models import TemporalMetrics
from repopeek.temporal.miner import CommitRecord, GitTemporalMiner


def evaluate_temporal_cochange(
    commits: Sequence[CommitRecord],
    cutoff_time: Optional[float] = None,
    half_lives: Sequence[float] = (30.0, 90.0, 180.0, 365.0),
) -> Dict[str, TemporalMetrics]:
    """Evaluate temporal co-change predictive accuracy across multiple decay half-lives.

    Ensures ZERO future leakage by training only on commits prior to cutoff_time.
    Tests predictive power on subsequent commits after cutoff_time.
    """
    if not commits or len(commits) < 4:
        # Fallback default if not enough commit history
        return {
            f"{int(hl)}d": TemporalMetrics(half_life_days=hl)
            for hl in half_lives
        }

    # Sort commits chronologically ascending
    sorted_commits = sorted(commits, key=lambda c: c.timestamp)

    if cutoff_time is None:
        # Use 70% chronological split point
        split_idx = max(2, int(len(sorted_commits) * 0.70))
        cutoff_time = sorted_commits[split_idx].timestamp

    train_commits = [c for c in sorted_commits if c.timestamp <= cutoff_time]
    test_commits = [c for c in sorted_commits if c.timestamp > cutoff_time and len(c.files) >= 2]

    if not train_commits or not test_commits:
        return {
            f"{int(hl)}d": TemporalMetrics(half_life_days=hl)
            for hl in half_lives
        }

    results: Dict[str, TemporalMetrics] = {}

    for hl in half_lives:
        miner = GitTemporalMiner(
            half_life_days=hl,
            min_confidence=0.01,
            min_commits=1,
            max_files_per_commit=100,
        )
        # Compute co-changes using ONLY training commits with reference_time = cutoff_time
        relations = miner.compute_co_changes(commits=train_commits, reference_time=cutoff_time)

        # Build prediction map: file_a -> ranked list of file_b
        pred_map: Dict[str, List[str]] = defaultdict(list)
        for r in relations:
            pred_map[r.file_a].append(r.file_b)

        p5_sum, r5_sum = 0.0, 0.0
        p10_sum, r10_sum = 0.0, 0.0
        mrr_sum = 0.0
        eval_cases = 0

        for c in test_commits:
            unique_files = list(set(c.files))
            for f_a in unique_files:
                actual_targets = set(unique_files) - {f_a}
                if not actual_targets:
                    continue

                predicted = pred_map.get(f_a, [])
                top5 = predicted[:5]
                top10 = predicted[:10]

                # Precision@5 and Recall@5
                tp5 = len(set(top5) & actual_targets)
                p5_sum += tp5 / 5.0 if top5 else 0.0
                r5_sum += tp5 / len(actual_targets)

                # Precision@10 and Recall@10
                tp10 = len(set(top10) & actual_targets)
                p10_sum += tp10 / 10.0 if top10 else 0.0
                r10_sum += tp10 / len(actual_targets)

                # Reciprocal rank of first correct co-change
                mrr_sum += reciprocal_rank(predicted, list(actual_targets), matcher=lambda a, b: a == b)
                eval_cases += 1

        if eval_cases > 0:
            results[f"{int(hl)}d"] = TemporalMetrics(
                half_life_days=hl,
                precision_at_5=round(p5_sum / eval_cases, 4),
                recall_at_5=round(r5_sum / eval_cases, 4),
                precision_at_10=round(p10_sum / eval_cases, 4),
                recall_at_10=round(r10_sum / eval_cases, 4),
                mrr=round(mrr_sum / eval_cases, 4),
            )
        else:
            results[f"{int(hl)}d"] = TemporalMetrics(half_life_days=hl)

    return results
