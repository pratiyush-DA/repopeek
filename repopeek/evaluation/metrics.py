"""Core evaluation metrics for retrieval, graph traversal, confidence, and context reduction."""

import math
from typing import Any, Callable, List, Optional, Sequence, Set, Tuple

from repopeek.evaluation.models import CalibrationBucket


def matches_symbol(candidate: str, gold: str) -> bool:
    """Check if candidate symbol matches gold target.

    Handles qualified names, node URIs, and dotted identifiers:
    e.g. 'py:src/billing/invoice.py::InvoiceParser.parse' matches:
      - 'py:src/billing/invoice.py::InvoiceParser.parse'
      - 'InvoiceParser.parse'
      - 'invoice.py::InvoiceParser.parse'
      - 'InvoiceParser' (if gold is class)
    """
    cand_clean = candidate.strip().lower()
    gold_clean = gold.strip().lower()

    if cand_clean == gold_clean:
        return True

    # URI suffix matching
    if cand_clean.endswith(f"::{gold_clean}") or cand_clean.endswith(f".{gold_clean}"):
        return True

    # Dotted suffix matching on URI path
    if "::" in cand_clean:
        qual_name = cand_clean.split("::", 1)[1]
        if qual_name == gold_clean or qual_name.endswith(f".{gold_clean}"):
            return True

    return False


def matches_file(candidate: str, gold: str) -> bool:
    """Check if candidate file path matches gold file."""
    c_norm = candidate.replace("\\", "/").strip().lstrip("./").lower()
    g_norm = gold.replace("\\", "/").strip().lstrip("./").lower()
    return c_norm == g_norm or c_norm.endswith(g_norm) or g_norm.endswith(c_norm)


def recall_at_k(
    retrieved: Sequence[str],
    gold: Sequence[str],
    k: int,
    matcher: Callable[[str, str], bool] = matches_symbol,
) -> float:
    """Calculate Recall@K: 1.0 if at least one gold item appears in top K, else 0.0."""
    if not gold:
        return 1.0
    top_k = retrieved[:k]
    for item in top_k:
        if any(matcher(item, g) for g in gold):
            return 1.0
    return 0.0


def reciprocal_rank(
    retrieved: Sequence[str],
    gold: Sequence[str],
    matcher: Callable[[str, str], bool] = matches_symbol,
) -> float:
    """Calculate reciprocal rank: 1 / (first_hit_rank + 1) (1-indexed)."""
    if not gold:
        return 0.0
    for rank_idx, item in enumerate(retrieved):
        if any(matcher(item, g) for g in gold):
            return 1.0 / (rank_idx + 1)
    return 0.0


def mean_reciprocal_rank(
    all_retrieved: Sequence[Sequence[str]],
    all_gold: Sequence[Sequence[str]],
    matcher: Callable[[str, str], bool] = matches_symbol,
) -> float:
    """Calculate Mean Reciprocal Rank (MRR) across all queries."""
    if not all_retrieved or not all_gold:
        return 0.0
    n = min(len(all_retrieved), len(all_gold))
    if n == 0:
        return 0.0
    total_rr = sum(
        reciprocal_rank(all_retrieved[i], all_gold[i], matcher=matcher)
        for i in range(n)
    )
    return round(total_rr / n, 4)


def precision_recall_f1(retrieved: Set[Any], gold: Set[Any]) -> Tuple[float, float, float]:
    """Calculate Precision, Recall, and F1 score for set predictions."""
    if not gold and not retrieved:
        return 1.0, 1.0, 1.0
    if not retrieved:
        return 0.0, 0.0, 0.0
    if not gold:
        return 0.0, 1.0, 0.0

    tp = len(retrieved & gold)
    precision = tp / len(retrieved)
    recall = tp / len(gold)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return round(precision, 4), round(recall, 4), round(f1, 4)


def brier_score(predictions: Sequence[float], outcomes: Sequence[int]) -> float:
    """Calculate Brier score: mean squared error of probabilistic predictions."""
    if not predictions or not outcomes:
        return 0.0
    n = min(len(predictions), len(outcomes))
    if n == 0:
        return 0.0
    total_sq_err = sum((float(predictions[i]) - float(outcomes[i])) ** 2 for i in range(n))
    return round(total_sq_err / n, 4)


def calibration_buckets(
    predictions: Sequence[float],
    outcomes: Sequence[int],
    n_buckets: int = 10,
) -> List[CalibrationBucket]:
    """Partition predictions into calibration buckets (e.g. 0.0-0.1, 0.1-0.2, etc.)."""
    n = min(len(predictions), len(outcomes))
    if n == 0:
        return []

    bucket_width = 1.0 / n_buckets
    buckets_pred: List[List[float]] = [[] for _ in range(n_buckets)]
    buckets_out: List[List[int]] = [[] for _ in range(n_buckets)]

    for i in range(n):
        p = min(0.9999, max(0.0, float(predictions[i])))
        bucket_idx = int(p / bucket_width)
        bucket_idx = min(n_buckets - 1, max(0, bucket_idx))
        buckets_pred[bucket_idx].append(p)
        buckets_out[bucket_idx].append(outcomes[i])

    result: List[CalibrationBucket] = []
    for b in range(n_buckets):
        b_low = b * bucket_width
        b_high = (b + 1) * bucket_width
        label = f"{b_low:.1f}-{b_high:.1f}"
        preds = buckets_pred[b]
        outs = buckets_out[b]
        count = len(preds)

        avg_pred = round(sum(preds) / count, 3) if count > 0 else round((b_low + b_high) / 2.0, 3)
        actual_acc = round(sum(outs) / count, 3) if count > 0 else 0.0

        result.append(
            CalibrationBucket(
                bucket_range=label,
                predicted_confidence=avg_pred,
                actual_accuracy=actual_acc,
                count=count,
            )
        )

    return result


def negative_precision_and_false_inclusion(
    retrieved_items: Sequence[str],
    excluded_items: Sequence[str],
    matcher: Callable[[str, str], bool] = matches_symbol,
) -> Tuple[float, float]:
    """Measure how well excluded symbols/paths are kept out of retrieval.

    Returns:
        (negative_precision, false_inclusion_rate)
    """
    if not excluded_items:
        return 1.0, 0.0

    false_inclusions = 0
    for excl in excluded_items:
        if any(matcher(ret, excl) or excl.lower() in ret.lower() for ret in retrieved_items):
            false_inclusions += 1

    fir = round(false_inclusions / len(excluded_items), 4)
    neg_prec = round(1.0 - fir, 4)
    return neg_prec, fir


def token_reduction(context_tokens: int, baseline_tokens: int) -> float:
    """Calculate percentage context reduction vs whole repository baseline."""
    if baseline_tokens <= 0:
        return 0.0
    reduction = max(0.0, 1.0 - (float(context_tokens) / float(baseline_tokens)))
    return round(reduction * 100.0, 2)


def percentile(values: Sequence[float], p: float) -> float:
    """Calculate p-th percentile from a sequence of values (p in [0, 100])."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return round(float(sorted_vals[int(k)]), 2)
    d0 = sorted_vals[int(f)] * (c - k)
    d1 = sorted_vals[int(c)] * (k - f)
    return round(float(d0 + d1), 2)
