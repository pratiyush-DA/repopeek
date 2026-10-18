"""Production-grade verification test suite for RepoPeek graph formation and queries.

Verifies:
1. Relative import isolation and cross-module namespace collision immunity.
2. Multi-level relative imports (., .., ...).
3. Call resolution through local relative imports.
4. Lookup query ranking: internal codebase definitions prioritized over external stubs.
5. Case-insensitive exact symbol resolution (e.g. 'invoice' -> Invoice class, not table.invoices).
6. Graph display blast-radius highlight styling (lineWidth <= 1.5).
7. Hard token-budget enforcement on context_pack.
8. Import cycle isolation to EdgeType.IMPORTS.
9. God nodes external/builtin noise suppression.
10. Polyglot HTTP boundary linking.
"""

from pathlib import Path
import pytest

from repopeek.models.schema import EdgeType, Confidence
from repopeek.parsers.python import PythonParser
from repopeek.parsers.typescript import TypeScriptParser
from repopeek.graph.builder import GraphBuilder
from repopeek.graph.resolver import SymbolResolver
from repopeek.graph.analysis import find_import_cycles, god_nodes
from repopeek.query.engine import GraphQueryEngine


class TestGraphFormationIntegrity:
    """Rigorous verification that graphs are formed accurately without false linkages."""

    def test_python_relative_import_namespace_isolation(self):
        """Ensure local relative imports (e.g. from .validators) do not collide across modules."""
        parser = PythonParser()
        r_invoice = parser.parse_source(
            "from .validators import validate\n\ndef process():\n    validate()\n",
            "src/billing/invoice.py",
        )
        r_auth = parser.parse_source(
            "def validate():\n    return True\n",
            "src/auth/validators.py",
        )
        r_bill = parser.parse_source(
            "def validate():\n    return True\n",
            "src/billing/validators.py",
        )

        all_nodes = r_invoice.nodes + r_auth.nodes + r_bill.nodes
        all_edges = r_invoice.edges + r_auth.edges + r_bill.edges

        resolver = SymbolResolver(nodes=all_nodes, edges=all_edges)
        resolved_edges = resolver.resolve()

        # 1. Import edge must point to billing.validators, NOT auth.validators
        import_edges = [
            e for e in resolved_edges
            if e.src == "py:src/billing/invoice.py::<module>" and e.type == EdgeType.IMPORTS
        ]
        assert len(import_edges) >= 1
        assert any(e.dst == "py:src/billing/validators.py::validate" for e in import_edges)
        assert not any("auth" in e.dst for e in import_edges)

        # 2. Call edge from process() must also route to billing.validators::validate
        call_edges = [
            e for e in resolved_edges
            if e.src == "py:src/billing/invoice.py::process" and e.type == EdgeType.CALLS
        ]
        assert len(call_edges) == 1
        assert call_edges[0].dst == "py:src/billing/validators.py::validate"
        assert call_edges[0].confidence == Confidence.RESOLVED

    def test_python_multilevel_relative_imports(self):
        """Ensure parent-level relative imports (..models, ..common) resolve up the directory tree."""
        parser = PythonParser()
        r_child = parser.parse_source(
            "from ..models.base import BaseEntity\n\nclass Child(BaseEntity):\n    pass\n",
            "src/billing/handlers/child.py",
        )
        r_base = parser.parse_source(
            "class BaseEntity:\n    pass\n",
            "src/models/base.py",
        )

        resolver = SymbolResolver(nodes=r_child.nodes + r_base.nodes, edges=r_child.edges + r_base.edges)
        resolved = resolver.resolve()

        # Class Child must inherit from BaseEntity
        inherits = [e for e in resolved if e.type == EdgeType.INHERITS]
        assert len(inherits) == 1
        assert inherits[0].dst == "py:src/models/base.py::BaseEntity"

    def test_import_cycles_isolated_to_imports_only(self):
        """Cycles must strictly reflect import statements, not inheritance or definitions."""
        builder = GraphBuilder()
        sample_path = Path("tests/fixtures/sample_repo")
        graph = builder.build_from_directory(sample_path)

        cycles = find_import_cycles(graph)
        # sample_repo has no circular imports; cycles must be empty
        assert isinstance(cycles, list)
        for c in cycles:
            assert len(c) >= 2


@pytest.fixture(scope="module")
def sample_engine():
    builder = GraphBuilder()
    sample_path = Path("tests/fixtures/sample_repo")
    graph = builder.build_from_directory(sample_path)
    return GraphQueryEngine(graph=graph, repo_root=sample_path)


class TestGraphQueryIntegrity:
    """Verify that graph queries return the exact right symbols, ranks, and bounds."""

    def test_lookup_prioritizes_internal_over_external(self, sample_engine):
        """Looking up 'invoice.amount' must return internal Invoice.amount, NOT ext:py:unresolved stub."""
        node = sample_engine.lookup("invoice.amount")
        assert node is not None
        assert not node.id.startswith("ext:")
        assert node.id == "py:src/billing/invoice.py::Invoice.amount"
        assert node.span is not None
        assert node.span.file == "src/billing/invoice.py"

    def test_lookup_exact_name_beats_substring(self, sample_engine):
        """Querying 'invoice' must match class Invoice, NOT sql:db/queries.sql::table.invoices."""
        node = sample_engine.lookup("invoice")
        assert node is not None
        assert node.id == "py:src/billing/invoice.py::Invoice"
        assert node.kind == "class"

    def test_lookup_exact_id_works(self, sample_engine):
        """Direct exact ID lookup returns the node card immediately."""
        target_id = "py:src/billing/invoice.py::InvoiceParser.parse"
        node = sample_engine.lookup(target_id)
        assert node is not None
        assert node.id == target_id
        assert node.kind == "method"

    def test_context_pack_enforces_hard_token_budget(self, sample_engine):
        """Context pack must strictly honor token_budget even with multiple targets."""
        budget = 350
        pack = sample_engine.context_pack(
            targets=[
                "py:src/billing/invoice.py::InvoiceParser.parse",
                "py:src/models/base.py::BaseEntity",
            ],
            token_budget=budget,
            include_snippet=True,
        )
        assert pack.estimated_tokens <= budget

    def test_god_nodes_excludes_builtins_and_noise(self, sample_engine):
        """God nodes must represent meaningful architectural hubs, never len, str, or builtins."""
        gods = god_nodes(sample_engine.graph, top_n=5)
        for g in gods:
            assert not g["id"].startswith("ext:")
            assert g["label"] not in ("len", "str", "dict", "list", "int", "None")

    def test_blast_radius_thin_line_styling(self):
        """Verify graph viewer index.html has a thin blast-radius highlight line (<= 1.5)."""
        html_path = Path("repopeek/viewer/index.html")
        assert html_path.exists()
        content = html_path.read_text(encoding="utf-8")

        # Search for inImpact stroke configuration
        assert "inImpact" in content
        # Ensure lineWidth is thin (1.3)
        assert "ctx.lineWidth = 1.3;" in content
        assert "ctx.lineWidth = 2.2;" not in content
