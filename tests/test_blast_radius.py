"""Tests for mathematical traversal confidence scoring and evidence-backed blast radius."""

import math
from pathlib import Path
import pytest

from repopeek.graph.blast_radius import (
    AffectedNode,
    BlastRadiusReport,
    calculate_combined_confidence,
    calculate_graph_score,
    calculate_path_confidence,
    compute_blast_radius,
    get_edge_prior,
)
from repopeek.models.schema import (
    CanonicalGraph,
    Confidence,
    Edge,
    EdgeType,
    Evidence,
    NodeCard,
    NodeFacts,
    NodeStory,
    Span,
)
from repopeek.query.engine import GraphQueryEngine


def _make_blast_radius_graph() -> CanonicalGraph:
    """Helper creating a multi-hop graph with known paths and confidences.

    Graph topology:
      A (target) -> B (hop 1, direct, CALLS, resolved)
      A -> C (hop 1, direct, IMPORTS, resolved)
      B -> D (hop 2, indirect, CALLS, resolved)
      C -> D (hop 2, indirect, CALLS, resolved)  <-- Multi-path convergence to D
      D -> E (hop 3, indirect, DYNAMIC, ambiguous)
      E -> F (hop 4, excluded, UNRESOLVED, unresolved)
    """
    graph = CanonicalGraph(
        schema_version="1.0.0",
        tool_version="0.1.0",
        repo_commit="commit123",
        dirty=False,
    )

    nodes = [
        NodeCard(
            id="python:app/service.py::ServiceA",
            kind="class",
            sig="class ServiceA",
            span=Span(file="app/service.py", start=1, end=50),
            facts=NodeFacts(),
            content_hash="hA",
        ),
        NodeCard(
            id="python:app/billing.py::charge",
            kind="function",
            sig="def charge() -> bool",
            span=Span(file="app/billing.py", start=10, end=30),
            facts=NodeFacts(),
            content_hash="hB",
        ),
        NodeCard(
            id="python:app/helpers.py::tax_util",
            kind="function",
            sig="def tax_util() -> float",
            span=Span(file="app/helpers.py", start=5, end=15),
            facts=NodeFacts(),
            content_hash="hC",
        ),
        NodeCard(
            id="python:app/gateway.py::submit_tx",
            kind="function",
            sig="def submit_tx() -> dict",
            span=Span(file="app/gateway.py", start=20, end=40),
            facts=NodeFacts(),
            content_hash="hD",
        ),
        NodeCard(
            id="python:app/external.py::send_webhook",
            kind="function",
            sig="def send_webhook() -> None",
            span=Span(file="app/external.py", start=1, end=10),
            facts=NodeFacts(),
            content_hash="hE",
        ),
        NodeCard(
            id="python:app/legacy.py::notify_sink",
            kind="function",
            sig="def notify_sink() -> None",
            span=Span(file="app/legacy.py", start=100, end=120),
            facts=NodeFacts(),
            content_hash="hF",
        ),
    ]

    for n in nodes:
        graph.add_node(n)

    # A -> B (CALLS, resolved, step conf 0.95)
    graph.add_edge(Edge(
        src=nodes[0].id,
        dst=nodes[1].id,
        type=EdgeType.CALLS,
        confidence=Confidence.RESOLVED,
        evidence=Evidence(file="app/service.py", start_line=15, end_line=15, how_derived="ast:call"),
    ))

    # A -> C (IMPORTS, resolved, step conf 0.80)
    graph.add_edge(Edge(
        src=nodes[0].id,
        dst=nodes[2].id,
        type=EdgeType.IMPORTS,
        confidence=Confidence.RESOLVED,
        evidence=Evidence(file="app/service.py", start_line=2, end_line=2, how_derived="ast:import"),
    ))

    # B -> D (CALLS, resolved, step conf 0.95)
    graph.add_edge(Edge(
        src=nodes[1].id,
        dst=nodes[3].id,
        type=EdgeType.CALLS,
        confidence=Confidence.RESOLVED,
        evidence=Evidence(file="app/billing.py", start_line=22, end_line=22, how_derived="ast:call"),
    ))

    # C -> D (CALLS, resolved, step conf 0.95)
    graph.add_edge(Edge(
        src=nodes[2].id,
        dst=nodes[3].id,
        type=EdgeType.CALLS,
        confidence=Confidence.RESOLVED,
        evidence=Evidence(file="app/helpers.py", start_line=10, end_line=10, how_derived="ast:call"),
    ))

    # D -> E (CALLS, ambiguous, step conf 0.50)
    graph.add_edge(Edge(
        src=nodes[3].id,
        dst=nodes[4].id,
        type=EdgeType.CALLS,
        confidence=Confidence.AMBIGUOUS,
        evidence=Evidence(file="app/gateway.py", start_line=35, end_line=35, how_derived="dynamic:dispatch"),
    ))

    # E -> F (CALLS, unresolved, step conf 0.30)
    graph.add_edge(Edge(
        src=nodes[4].id,
        dst=nodes[5].id,
        type=EdgeType.CALLS,
        confidence=Confidence.UNRESOLVED,
        evidence=Evidence(file="app/external.py", start_line=5, end_line=5, how_derived="heuristic:guess"),
    ))

    return graph


def test_edge_priors():
    """Verify edge prior calculation according to relationship and certainty."""
    e1 = Edge(src="A", dst="B", type=EdgeType.CALLS, confidence=Confidence.RESOLVED)
    assert get_edge_prior(e1) == 0.95

    e2 = Edge(src="A", dst="B", type=EdgeType.IMPORTS, confidence=Confidence.RESOLVED)
    assert get_edge_prior(e2) == 0.80

    e3 = Edge(src="A", dst="B", type=EdgeType.CALLS, confidence=Confidence.AMBIGUOUS)
    assert get_edge_prior(e3) == 0.50

    e4 = Edge(src="A", dst="B", type=EdgeType.CALLS, confidence=Confidence.UNRESOLVED)
    assert get_edge_prior(e4) == 0.30


def test_path_confidence_formula():
    """Verify single-path confidence calculation with hop decay."""
    # Hop 1 (h=1): PathConfidence = min(0.99, c_1 * exp(0)) = 0.95
    p1 = calculate_path_confidence([0.95])
    assert p1 == 0.95

    # Hop 2 (h=2): (0.95 * 0.95) * exp(-0.25)
    expected_p2 = min(0.99, (0.95 * 0.95) * math.exp(-0.25))
    p2 = calculate_path_confidence([0.95, 0.95])
    assert math.isclose(p2, expected_p2, rel_tol=1e-4)

    # Empty path returns 0.0
    assert calculate_path_confidence([]) == 0.0


def test_multi_path_combination():
    """Verify multi-path confidence reinforcement."""
    # Single path equals itself
    assert calculate_combined_confidence([0.70]) == 0.70

    # Two paths: 1 - (1 - 0.70) * (1 - 0.50) = 1 - 0.15 = 0.85
    p_combined = calculate_combined_confidence([0.70, 0.50])
    assert math.isclose(p_combined, 0.85, rel_tol=1e-4)

    # Capped at 0.99
    assert calculate_combined_confidence([0.95, 0.95, 0.95]) <= 0.99


def test_graph_score_distance_decay():
    """Verify distance decay factor exp(-0.70 * (d - 1))."""
    # At d=1: GraphScore = combined_conf * exp(0) = combined_conf
    assert calculate_graph_score(0.85, distance=1) == 0.85

    # At d=2: GraphScore = 0.85 * exp(-0.70)
    expected_d2 = round(0.85 * math.exp(-0.70), 6)
    assert calculate_graph_score(0.85, distance=2) == expected_d2

    # At d=3: GraphScore = 0.85 * exp(-1.40)
    expected_d3 = round(0.85 * math.exp(-1.40), 6)
    assert calculate_graph_score(0.85, distance=3) == expected_d3


def test_compute_blast_radius_partitioning():
    """Verify direct, indirect, and excluded partitioning on sample graph."""
    graph = _make_blast_radius_graph()
    report = compute_blast_radius(
        graph=graph,
        target_id="python:app/service.py::ServiceA",
        max_depth=5,
        direction="downstream",
        confidence_threshold=0.20,
    )

    assert report.found is True
    assert report.target_id == "python:app/service.py::ServiceA"
    assert report.target_citation == "app/service.py:1-50"

    # Direct nodes: charge (d=1, CALLS, conf 0.95) and tax_util (d=1, IMPORTS, conf 0.80)
    direct_ids = {n.node_id for n in report.direct}
    assert "python:app/billing.py::charge" in direct_ids
    assert "python:app/helpers.py::tax_util" in direct_ids

    # Indirect nodes: gateway (d=2, multi-path reinforced)
    indirect_ids = {n.node_id for n in report.indirect}
    assert "python:app/gateway.py::submit_tx" in indirect_ids

    # Verify multi-path reinforcement for gateway
    gateway_node = next(n for n in report.indirect if "submit_tx" in n.node_id)
    assert gateway_node.distance == 2
    assert len(gateway_node.paths) == 2
    # Multi-path combined confidence must be strictly higher than individual path confidences
    assert gateway_node.combined_confidence > gateway_node.paths[0].path_confidence
    assert gateway_node.citation == "app/gateway.py:20-40"

    # Excluded nodes: legacy notify_sink (d=4, confidence decayed below 0.20 threshold)
    excluded_ids = {e.node_id for e in report.excluded}
    assert "python:app/legacy.py::notify_sink" in excluded_ids
    legacy_excluded = next(e for e in report.excluded if "notify_sink" in e.node_id)
    assert "below minimum threshold" in legacy_excluded.exclusion_reason
    assert legacy_excluded.confidence < 0.20

    # Summary metrics
    assert report.metrics["direct_count"] == 2
    assert report.metrics["indirect_count"] >= 1
    assert report.metrics["excluded_count"] >= 1


def test_graph_query_engine_blast_radius_and_impact():
    """Verify integration of blast_radius and impact in GraphQueryEngine."""
    graph = _make_blast_radius_graph()
    engine = GraphQueryEngine(graph)

    # 1. Test blast_radius() method returning BlastRadiusReport
    report: BlastRadiusReport = engine.blast_radius("ServiceA", max_depth=5, direction="downstream")
    assert report.found is True
    assert len(report.direct) == 2
    assert len(report.indirect) >= 1

    # 2. Test impact() method returning backward-compatible enriched dict
    impact_dict = engine.impact("ServiceA", max_depth=5, direction="downstream")
    assert impact_dict["found"] is True
    assert impact_dict["target"] == "python:app/service.py::ServiceA"
    assert impact_dict["direct_count"] == 2
    assert impact_dict["indirect_count"] >= 1
    assert impact_dict["excluded_count"] >= 1

    # Verify citation and confidence presence on affected nodes
    sample_direct = impact_dict["direct"][0]
    assert "confidence" in sample_direct
    assert "citation" in sample_direct
    assert sample_direct["category"] == "direct"
    assert sample_direct["distance"] == 1


def test_blast_radius_target_not_found():
    """Verify graceful handling when target node does not exist."""
    graph = _make_blast_radius_graph()
    report = compute_blast_radius(graph, target_id="nonexistent_symbol")
    assert report.found is False
    assert len(report.direct) == 0
    assert len(report.indirect) == 0
    assert len(report.excluded) == 0
