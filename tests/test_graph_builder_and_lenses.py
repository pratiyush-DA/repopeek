"""Unit tests for RepoPeek GraphBuilder, SymbolResolver, and Multi-Lens projections."""

from pathlib import Path
import pytest

from repopeek.graph.builder import GraphBuilder
from repopeek.graph.lenses import (
    get_call_lens,
    get_class_lens,
    get_module_lens,
    get_symbol_lens,
)
from repopeek.models.schema import Confidence, EdgeType

SAMPLE_REPO_DIR = Path("tests/fixtures/sample_repo")


@pytest.fixture(scope="module")
def sample_graph():
    builder = GraphBuilder()
    return builder.build_from_directory(SAMPLE_REPO_DIR, repo_commit="test_commit_sha")


def test_symbol_resolver_cross_file_calls(sample_graph):
    """Verify SymbolResolver rebinds function calls to concrete target node IDs."""
    call_edges = [
        e for e in sample_graph.edges
        if e.src == "py:src/billing/invoice.py::InvoiceParser.parse" and e.type == EdgeType.CALLS
    ]
    targets = {e.dst for e in call_edges}

    # Calls validate_invoice in validators.py
    assert "py:src/billing/validators.py::validate_invoice" in targets
    # Calls local Invoice class constructor
    assert "py:src/billing/invoice.py::Invoice" in targets


def test_symbol_resolver_cross_file_inheritance(sample_graph):
    """Verify SymbolResolver resolves base classes across modules."""
    inherits_edges = [
        e for e in sample_graph.edges
        if e.src == "py:src/billing/invoice.py::Invoice" and e.type == EdgeType.INHERITS
    ]
    assert len(inherits_edges) == 1
    assert inherits_edges[0].dst == "py:src/models/base.py::AuditableEntity"
    assert inherits_edges[0].confidence == Confidence.RESOLVED


def test_symbol_resolver_external_imports(sample_graph):
    """Verify third-party stdlib imports are marked with Confidence.EXTERNAL."""
    import_edges = [
        e for e in sample_graph.edges
        if e.src == "py:src/billing/invoice.py::<module>" and e.type == EdgeType.IMPORTS
    ]
    external_dsts = {e.dst for e in import_edges if e.confidence == Confidence.EXTERNAL}
    assert any("typing.Dict" in d or "typing.Optional" in d for d in external_dsts)


def test_graph_builder_full_assembly(sample_graph):
    """Verify complete multi-language graph construction and NetworkX conversion."""
    assert len(sample_graph.nodes) >= 30
    assert len(sample_graph.edges) >= 40
    assert sample_graph.repo_commit == "test_commit_sha"

    # Export to NetworkX
    nx_graph = GraphBuilder.to_networkx(sample_graph)
    assert nx_graph.number_of_nodes() >= len(sample_graph.nodes)
    assert all(nid in nx_graph for nid in sample_graph.nodes)
    assert nx_graph.has_node("py:src/billing/invoice.py::InvoiceParser.parse")

    # Validate graph integrity
    issues = GraphBuilder.validate_graph(sample_graph)
    assert len(issues) == 0


def test_module_lens(sample_graph):
    """Verify Module Lens reflects file-to-file pipelines and imports."""
    mod_lens = get_module_lens(sample_graph)
    all_kinds = {n.kind for n in mod_lens.nodes.values()}
    assert all_kinds.issubset({"file", "module"})

    # Check that YAML pipeline script execution is captured
    runs_edges = [e for e in mod_lens.edges if e.type == EdgeType.RUNS_SCRIPT]
    assert any("pipeline.yaml" in e.src and "run_pipeline.sh" in e.dst for e in runs_edges)


def test_call_lens(sample_graph):
    """Verify Call Lens contains only callable nodes and invocation edges."""
    call_lens = get_call_lens(sample_graph)
    assert all(e.type == EdgeType.CALLS for e in call_lens.edges)
    assert len(call_lens.edges) >= 3

    # InvoiceParser.parse calling validate_invoice must be present
    assert any(
        "InvoiceParser.parse" in e.src and "validate_invoice" in e.dst
        for e in call_lens.edges
    )


def test_class_lens(sample_graph):
    """Verify Class Lens captures OOP hierarchy and methods."""
    class_lens = get_class_lens(sample_graph)
    assert all(e.type in (EdgeType.INHERITS, EdgeType.DEFINED_IN) for e in class_lens.edges)

    # AuditableEntity -> BaseEntity inheritance
    assert any(
        "AuditableEntity" in e.src and "BaseEntity" in e.dst
        for e in class_lens.edges if e.type == EdgeType.INHERITS
    )
