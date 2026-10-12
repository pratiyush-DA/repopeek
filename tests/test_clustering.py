"""Tests for community detection, cohesion scoring, and community labeling."""

import pytest
from repopeek.graph.clustering import (
    compute_cohesion_scores,
    detect_communities,
    generate_community_labels,
)
from repopeek.models.schema import CanonicalGraph, Edge, EdgeType, NodeCard, Span


def _build_clustered_graph() -> CanonicalGraph:
    graph = CanonicalGraph()

    # Community A: Auth subsystem (3 tightly connected nodes)
    a1 = NodeCard(id="py:auth/login.py::login", kind="function", sig="login()", span=Span(file="auth/login.py", start=1, end=10), content_hash="h1")
    a2 = NodeCard(id="py:auth/token.py::generate_token", kind="function", sig="generate_token()", span=Span(file="auth/token.py", start=1, end=10), content_hash="h2")
    a3 = NodeCard(id="py:auth/user.py::User", kind="class", sig="User", span=Span(file="auth/user.py", start=1, end=20), content_hash="h3")

    # Community B: Billing subsystem (3 tightly connected nodes)
    b1 = NodeCard(id="py:billing/invoice.py::Invoice", kind="class", sig="Invoice", span=Span(file="billing/invoice.py", start=1, end=20), content_hash="h4")
    b2 = NodeCard(id="py:billing/pay.py::process_payment", kind="function", sig="process_payment()", span=Span(file="billing/pay.py", start=1, end=15), content_hash="h5")
    b3 = NodeCard(id="py:billing/tax.py::calc_tax", kind="function", sig="calc_tax()", span=Span(file="billing/tax.py", start=1, end=15), content_hash="h6")

    # Bridge between them
    for n in [a1, a2, a3, b1, b2, b3]:
        graph.add_node(n)

    # Intra-community A edges
    graph.add_edge(Edge(src=a1.id, dst=a2.id, type=EdgeType.CALLS))
    graph.add_edge(Edge(src=a1.id, dst=a3.id, type=EdgeType.CALLS))
    graph.add_edge(Edge(src=a2.id, dst=a3.id, type=EdgeType.CALLS))

    # Intra-community B edges
    graph.add_edge(Edge(src=b2.id, dst=b1.id, type=EdgeType.CALLS))
    graph.add_edge(Edge(src=b2.id, dst=b3.id, type=EdgeType.CALLS))
    graph.add_edge(Edge(src=b1.id, dst=b3.id, type=EdgeType.CALLS))

    # Single sparse cross-community bridge
    graph.add_edge(Edge(src=b2.id, dst=a3.id, type=EdgeType.CALLS))

    return graph


def test_detect_communities_partitioning():
    graph = _build_clustered_graph()
    communities = detect_communities(graph)
    assert len(communities) >= 2

    # Verify nodes in the same subsystem are clustered together
    a_nodes = {"py:auth/login.py::login", "py:auth/token.py::generate_token", "py:auth/user.py::User"}
    b_nodes = {"py:billing/invoice.py::Invoice", "py:billing/pay.py::process_payment", "py:billing/tax.py::calc_tax"}

    # Find which community contains a1
    cid_a = next(cid for cid, members in communities.items() if "py:auth/login.py::login" in members)
    # Most auth nodes should be in cid_a
    overlap_a = set(communities[cid_a]).intersection(a_nodes)
    assert len(overlap_a) >= 2


def test_compute_cohesion_scores():
    graph = _build_clustered_graph()
    communities = detect_communities(graph)
    cohesion = compute_cohesion_scores(graph, communities)
    assert len(cohesion) == len(communities)
    for cid, score in cohesion.items():
        assert 0.0 <= score <= 1.0


def test_generate_community_labels():
    graph = _build_clustered_graph()
    communities = detect_communities(graph)
    labels = generate_community_labels(graph, communities)
    assert len(labels) == len(communities)
    label_values = list(labels.values())
    assert any("auth" in lbl.lower() for lbl in label_values)
    assert any("billing" in lbl.lower() for lbl in label_values)
