"""Unit tests for RepoPeek Python AST parser and syntax resilience."""

from pathlib import Path
import pytest

from repopeek.models.schema import Confidence, EdgeType
from repopeek.parsers.python import PythonParser


@pytest.fixture
def parser() -> PythonParser:
    return PythonParser()


def test_parse_simple_python_function(parser: PythonParser):
    code = '''"""Sample module docstring."""

def calculate_discount(price: float, rate: float = 0.1) -> float:
    """Calculate the discounted total price."""
    if price < 0:
        raise ValueError("Price cannot be negative")
    total = price * (1.0 - rate)
    return total
'''
    res = parser.parse_source(source=code, rel_path="utils/calc.py")
    assert res.is_success
    assert res.language == "python"

    # Module file card
    file_card = next(n for n in res.nodes if n.kind == "file")
    assert file_card.id == "py:utils/calc.py::<module>"
    assert file_card.story.text == "Sample module docstring."

    # Function card
    fn_card = next(n for n in res.nodes if n.kind == "function")
    assert fn_card.id == "py:utils/calc.py::calculate_discount"
    assert "calculate_discount" in fn_card.sig
    assert fn_card.facts.params == ["price", "rate"]
    assert fn_card.facts.returns == "float"
    assert fn_card.facts.complexity == 2  # base 1 + if 1
    assert "ValueError" in fn_card.facts.raises
    assert "price" in fn_card.facts.reads
    assert "total" in fn_card.facts.writes
    assert fn_card.story.text == "Calculate the discounted total price."

    # Edges
    defined_in = next(e for e in res.edges if e.type == EdgeType.DEFINED_IN)
    assert defined_in.src == fn_card.id
    assert defined_in.dst == file_card.id

    raises_edge = next(e for e in res.edges if e.type == EdgeType.RAISES)
    assert raises_edge.src == fn_card.id
    assert raises_edge.dst == "ValueError"


def test_parse_classes_and_inheritance(parser: PythonParser):
    code = '''class BaseWorker:
    """Base class for workers."""
    pass

class DataWorker(BaseWorker):
    """Worker that handles data processing."""

    def run(self, batch_size: int = 100) -> None:
        """Run batch processing."""
        self.step()

    def step(self) -> None:
        pass
'''
    res = parser.parse_source(source=code, rel_path="workers/worker.py")
    assert res.is_success
    assert len(res.nodes) >= 5  # file + 2 classes + 2 methods

    base_card = next(n for n in res.nodes if n.id == "py:workers/worker.py::BaseWorker")
    assert base_card.kind == "class"

    data_card = next(n for n in res.nodes if n.id == "py:workers/worker.py::DataWorker")
    assert data_card.kind == "class"
    assert "class DataWorker(BaseWorker)" in data_card.sig

    # Inheritance edge
    inherits_edge = next(e for e in res.edges if e.type == EdgeType.INHERITS)
    assert inherits_edge.src == data_card.id
    assert inherits_edge.dst == "BaseWorker"

    # Method card and calls
    run_method = next(n for n in res.nodes if n.id == "py:workers/worker.py::DataWorker.run")
    assert run_method.kind == "method"
    assert run_method.facts.params == ["self", "batch_size"]

    call_edge = next(e for e in res.edges if e.type == EdgeType.CALLS)
    assert call_edge.src == run_method.id
    assert "self.step" in call_edge.dst


def test_parse_embedded_sql(parser: PythonParser):
    code = '''def fetch_pending_orders(cursor, limit: int = 10):
    """Retrieve pending orders from database."""
    query = "SELECT order_id, customer_id, total FROM orders WHERE status = 'PENDING'"
    cursor.execute(query)
'''
    res = parser.parse_source(source=code, rel_path="db/orders.py")
    assert res.is_success

    sql_nodes = [n for n in res.nodes if n.kind == "sql_query"]
    assert len(sql_nodes) == 1
    sql_card = sql_nodes[0]
    assert "SELECT order_id" in sql_card.sig

    embed_edges = [e for e in res.edges if e.type == EdgeType.EMBEDS_SQL]
    assert len(embed_edges) == 1
    assert embed_edges[0].src == "py:db/orders.py::fetch_pending_orders"
    assert embed_edges[0].dst == sql_card.id


def test_parse_fixture_sample_repo_invoice(parser: PythonParser):
    sample_invoice = Path("tests/fixtures/sample_repo/src/billing/invoice.py")
    res = parser.parse_file(sample_invoice, repo_root=Path("tests/fixtures/sample_repo"))
    assert res.is_success
    assert res.rel_path == "src/billing/invoice.py"

    # Node validation
    kinds = {n.kind for n in res.nodes}
    assert "file" in kinds
    assert "class" in kinds
    assert "method" in kinds
    assert "sql_query" in kinds

    # Verify InvoiceParser.parse method
    parse_method = next(
        n for n in res.nodes if n.id == "py:src/billing/invoice.py::InvoiceParser.parse"
    )
    assert parse_method.span.start >= 20
    assert "validate_invoice" in [e.dst for e in res.edges if e.type == EdgeType.CALLS]
    assert "ParseError" in [e.dst for e in res.edges if e.type == EdgeType.RAISES]

    # Verify embedded SQL in fixture
    sql_query = next(n for n in res.nodes if n.kind == "sql_query")
    assert "SELECT invoice_id" in sql_query.sig


def test_syntax_error_resilience(parser: PythonParser):
    broken_file = Path("tests/fixtures/sample_repo/src/scripts/broken_syntax.py")
    res = parser.parse_file(broken_file, repo_root=Path("tests/fixtures/sample_repo"))

    # Must NOT raise exception
    assert not res.is_success
    assert len(res.errors) == 1
    assert "SyntaxError" in res.errors[0]

    # Recovered file node
    file_node = next(n for n in res.nodes if n.kind == "file")
    assert file_node.story.confidence == "unresolved"

    # Recovered broken_function via fallback regex
    fn_node = next((n for n in res.nodes if n.id == "py:src/scripts/broken_syntax.py::broken_function"), None)
    assert fn_node is not None
    assert fn_node.kind == "function"
    assert fn_node.story.confidence == "unresolved"


def test_embedded_create_table_is_file_anchored_sql_table(parser: PythonParser):
    """CREATE TABLE inside a Python string becomes a file-anchored, name-searchable node.

    Regression (dcnc DCNC-005): embedded DDL was emitted as a generic query_L node and the
    created table surfaced as an unresolved external READ, so schema tasks could not resolve
    to the hosting .py file.
    """
    code = '''import sqlite3

def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pattern_cache (
            id INTEGER PRIMARY KEY,
            fingerprint_hash TEXT UNIQUE NOT NULL,
            patterns TEXT NOT NULL
        )
    """)
'''
    res = parser.parse_source(source=code, rel_path="backend/db.py")

    tbl = next((n for n in res.nodes if n.kind == "sql_table" and "pattern_cache" in n.id), None)
    assert tbl is not None
    assert tbl.id == "sql:backend/db.py::table.pattern_cache"
    assert tbl.span.file == "backend/db.py"
    assert "pattern_cache" in tbl.facts.writes
    # The created table is a definition, not an unresolved external read.
    read_dsts = [e.dst for e in res.edges if e.type == EdgeType.READS]
    assert "pattern_cache" not in read_dsts
