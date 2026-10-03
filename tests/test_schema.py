"""Unit tests for RepoPeek canonical property graph schema and data models."""

import pytest
from pydantic import ValidationError

from repopeek.models.schema import (
    CanonicalGraph,
    Confidence,
    Edge,
    EdgeType,
    Evidence,
    NodeCard,
    NodeFacts,
    NodeProvenance,
    NodeStory,
    Span,
)


def test_span_validation():
    """Verify Span enforces positive lines and start <= end."""
    valid_span = Span(file="src/billing/invoice.py", start=10, end=20)
    assert valid_span.start == 10
    assert valid_span.end == 20

    # Inverted line range must fail validation
    with pytest.raises(ValidationError):
        Span(file="src/billing/invoice.py", start=25, end=20)


def test_node_card_id_generation():
    """Verify stable URI node ID format."""
    node_id = NodeCard.make_id("py", "src/billing/invoice.py", "InvoiceParser.parse")
    assert node_id == "py:src/billing/invoice.py::InvoiceParser.parse"


def test_node_card_creation():
    """Verify NodeCard fields and serialization."""
    card = NodeCard(
        id="py:src/billing/invoice.py::InvoiceParser.parse",
        kind="method",
        sig="parse(self, raw: bytes) -> Invoice",
        span=Span(file="src/billing/invoice.py", start=41, end=88),
        facts=NodeFacts(
            calls=3,
            reads=["self.schema"],
            writes=["self._cache"],
            raises=["ParseError"],
            complexity=4,
        ),
        story=NodeStory(
            text="Validates raw bytes against schema and caches Invoice.",
            source="deterministic",
            confidence="high",
        ),
        content_hash="sha256:abc12345",
        provenance=NodeProvenance(commit="5559099", tool_version="0.1.0"),
    )

    data = card.model_dump()
    assert data["id"] == "py:src/billing/invoice.py::InvoiceParser.parse"
    assert data["facts"]["calls"] == 3
    assert data["story"]["source"] == "deterministic"


def test_edge_validation_and_canonical_graph():
    """Verify Edge types and CanonicalGraph manipulation."""
    graph = CanonicalGraph()

    func_node = NodeCard(
        id="py:src/billing/invoice.py::InvoiceParser.parse",
        kind="method",
        content_hash="hash1",
    )
    file_node = NodeCard(
        id="py:src/billing/invoice.py::File",
        kind="file",
        content_hash="hash2",
    )
    graph.add_node(func_node)
    graph.add_node(file_node)

    edge = Edge(
        src=func_node.id,
        dst=file_node.id,
        type=EdgeType.DEFINED_IN,
        confidence=Confidence.RESOLVED,
        evidence=Evidence(
            file="src/billing/invoice.py",
            start_line=41,
            end_line=88,
            how_derived="ast_def",
        ),
    )
    graph.add_edge(edge)

    assert graph.get_node(func_node.id) is not None
    assert len(graph.out_edges(func_node.id)) == 1
    assert graph.out_edges(func_node.id)[0].type == EdgeType.DEFINED_IN
    assert len(graph.in_edges(file_node.id)) == 1
