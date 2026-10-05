"""Level 2 evaluation: Graph dependency accuracy, traversal depth, and confidence calibration."""

from collections import deque
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from repopeek.evaluation.metrics import (
    brier_score,
    calibration_buckets,
    matches_symbol,
    precision_recall_f1,
)
from repopeek.evaluation.models import (
    ConfidenceMetrics,
    FailureCase,
    FailureCategory,
    GraphDepthMetrics,
)
from repopeek.graph.blast_radius import get_edge_prior
from repopeek.models.schema import CanonicalGraph, Edge


def normalize_edge_tuple(src: str, dst: str, edge_type: str) -> Tuple[str, str, str]:
    """Normalize edge components for order-independent evaluation."""
    return (src.strip().lower(), dst.strip().lower(), edge_type.strip().upper())


def matches_edge(retrieved: Tuple[str, str, str], gold: Tuple[str, str, str]) -> bool:
    """Check if retrieved (src, dst, type) matches gold tuple."""
    r_src, r_dst, r_type = retrieved
    g_src, g_dst, g_type = gold

    # Type must match (or allow wildcard ANY)
    if g_type != "ANY" and r_type != g_type:
        return False

    return matches_symbol(r_src, g_src) and matches_symbol(r_dst, g_dst)


def evaluate_graph_accuracy(
    gold_edges: Sequence[Dict[str, str]],
    graph: CanonicalGraph,
    depths: Sequence[int] = (1, 2, 3, 4),
) -> Tuple[Dict[int, GraphDepthMetrics], List[FailureCase]]:
    """Evaluate graph accuracy and relation discovery across traversal depths (1..4 hops).

    Measures Precision, Recall, and F1 at each depth.
    Detects GRAPH_MISSING_EDGE and GRAPH_FALSE_EDGE.
    """
    if not gold_edges:
        return {d: GraphDepthMetrics(depth=d) for d in depths}, []

    norm_gold = [
        (e["src"].strip().lower(), e["dst"].strip().lower(), e.get("type", "ANY").strip().upper())
        for e in gold_edges
    ]

    # Pre-index graph edges by source
    outgoing: Dict[str, List[Edge]] = {}
    for edge in graph.edges:
        outgoing.setdefault(edge.src, []).append(edge)

    depth_metrics: Dict[int, GraphDepthMetrics] = {}
    failures: List[FailureCase] = []

    for depth in depths:
        # Collect all reachable edges from gold sources within `depth` hops
        visited_edges: Set[Tuple[str, str, str]] = set()

        for g_src, _, _ in norm_gold:
            # Find matching start nodes in graph
            start_nodes = [nid for nid in graph.nodes if matches_symbol(nid, g_src)]
            if not start_nodes:
                continue

            for start_nid in start_nodes:
                queue: deque = deque([(start_nid, 1)])
                visited_nodes = {start_nid}

                while queue:
                    curr_nid, curr_d = queue.popleft()
                    if curr_d > depth:
                        continue

                    for edge in outgoing.get(curr_nid, []):
                        edge_type_str = edge.type.value if hasattr(edge.type, "value") else str(edge.type)
                        norm_e = (edge.src.strip().lower(), edge.dst.strip().lower(), edge_type_str.upper())
                        visited_edges.add(norm_e)

                        if edge.dst not in visited_nodes:
                            visited_nodes.add(edge.dst)
                            queue.append((edge.dst, curr_d + 1))

        # Calculate true positives at this depth
        tp_count = 0
        matched_gold_indices = set()

        for g_idx, g_edge in enumerate(norm_gold):
            if any(matches_edge(v_edge, g_edge) for v_edge in visited_edges):
                tp_count += 1
                matched_gold_indices.add(g_idx)

        total_retrieved = len(visited_edges)
        total_gold = len(norm_gold)

        precision = round(tp_count / total_retrieved, 4) if total_retrieved > 0 else 0.0
        recall = round(tp_count / total_gold, 4) if total_gold > 0 else 0.0
        f1 = round((2 * precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0

        depth_metrics[depth] = GraphDepthMetrics(
            depth=depth,
            precision=precision,
            recall=recall,
            f1=f1,
            evaluated_edges=total_retrieved,
        )

        # Record missing edge failures for gold edges missed at max depth
        if depth == max(depths):
            for g_idx, g_edge in enumerate(norm_gold):
                if g_idx not in matched_gold_indices:
                    failures.append(
                        FailureCase(
                            task_id=f"edge_{g_edge[0]}->{g_edge[1]}",
                            category=FailureCategory.GRAPH_MISSING_EDGE,
                            expected=f"{g_edge[0]} -[{g_edge[2]}]-> {g_edge[1]}",
                            retrieved=None,
                            explanation=(
                                f"Graph traversal up to depth {depth} failed to discover expected relationship "
                                f"{g_edge[0]} -[{g_edge[2]}]-> {g_edge[1]}."
                            ),
                        )
                    )

    return depth_metrics, failures


def evaluate_confidence_calibration(
    edge_predictions: Sequence[Tuple[float, bool]],
    n_buckets: int = 10,
) -> ConfidenceMetrics:
    """Evaluate statistical calibration of edge confidence scores.

    Args:
        edge_predictions: Sequence of (predicted_confidence, is_correct) pairs.
        n_buckets: Number of probability calibration bins.

    Returns:
        ConfidenceMetrics with Brier score, calibration bins, and error distributions.
    """
    if not edge_predictions:
        return ConfidenceMetrics()

    preds = [p[0] for p in edge_predictions]
    actuals = [1 if p[1] else 0 for p in edge_predictions]

    b_score = brier_score(preds, actuals)
    buckets = calibration_buckets(preds, actuals, n_buckets=n_buckets)

    correct_confs = [p for p, is_corr in edge_predictions if is_corr]
    incorrect_confs = [p for p, is_corr in edge_predictions if not is_corr]

    mean_corr = round(sum(correct_confs) / len(correct_confs), 4) if correct_confs else 0.0
    mean_incorr = round(sum(incorrect_confs) / len(incorrect_confs), 4) if incorrect_confs else 0.0

    return ConfidenceMetrics(
        brier_score=b_score,
        calibration_buckets=buckets,
        mean_correct_confidence=mean_corr,
        mean_incorrect_confidence=mean_incorr,
    )
