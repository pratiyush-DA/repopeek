"""Tests for Context Compiler, Constraint Extractor, and Change Plan Generator."""

import json
from pathlib import Path
import pytest

from repopeek.context import (
    ChangePlan,
    ChangePlanStep,
    ConstraintSet,
    ContextCompiler,
    ContextPackage,
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
from repopeek.storage.sqlite_cache import build_sqlite_cache


def _make_context_test_graph() -> CanonicalGraph:
    """Helper creating a sample graph for context compilation testing."""
    graph = CanonicalGraph(
        schema_version="1.0.0",
        tool_version="0.1.0",
        repo_commit="feedface",
        dirty=False,
    )

    n1 = NodeCard(
        id="python:billing/checkout.py::process_checkout",
        kind="function",
        sig="def process_checkout(cart_id: str, retry_count: int = 3) -> bool",
        span=Span(file="billing/checkout.py", start=10, end=40),
        facts=NodeFacts(
            calls=2,
            params=["cart_id: str", "retry_count: int = 3"],
            returns="bool",
            raises=["CheckoutError", "ValueError"],
        ),
        story=NodeStory(text="Orchestrates checkout transaction and initiates payment gateway"),
        content_hash="h1",
    )
    n2 = NodeCard(
        id="python:billing/gateway.py::charge_card",
        kind="function",
        sig="def charge_card(amount: float) -> str",
        span=Span(file="billing/gateway.py", start=5, end=25),
        facts=NodeFacts(calls=0, params=["amount: float"], returns="str"),
        story=NodeStory(text="Communicates with third-party payment gateway"),
        content_hash="h2",
    )
    n3 = NodeCard(
        id="sql:schema/orders.sql::table.orders",
        kind="sql_table",
        sig="CREATE TABLE orders (id INT, status VARCHAR(20))",
        span=Span(file="schema/orders.sql", start=1, end=10),
        facts=NodeFacts(calls=0),
        story=NodeStory(text="Stores order records and payment statuses"),
        content_hash="h3",
    )

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)

    # checkout -> charge_card (CALLS)
    graph.add_edge(Edge(
        src=n1.id,
        dst=n2.id,
        type=EdgeType.CALLS,
        confidence=Confidence.RESOLVED,
        evidence=Evidence(file="billing/checkout.py", start_line=25, end_line=25, how_derived="ast:call"),
    ))

    # checkout -> table.orders (WRITES)
    graph.add_edge(Edge(
        src=n1.id,
        dst=n3.id,
        type=EdgeType.WRITES,
        confidence=Confidence.RESOLVED,
        evidence=Evidence(file="billing/checkout.py", start_line=35, end_line=35, how_derived="sql:insert"),
    ))

    return graph


def test_context_compiler_basic(tmp_path: Path):
    graph = _make_context_test_graph()
    db_file = tmp_path / "cache.db"
    build_sqlite_cache(graph, db_file)

    engine = GraphQueryEngine(graph, storage_dir=tmp_path)
    compiler = ContextCompiler(engine)

    pkg: ContextPackage = compiler.compile(
        task="Update retry_count in process_checkout for failed payments",
        budget=1500,
        level=2,
    )

    assert pkg.task == "Update retry_count in process_checkout for failed payments"
    assert len(pkg.entrypoints) > 0
    assert any("process_checkout" in ep["node_id"] for ep in pkg.entrypoints)

    # Direct blast radius should capture charge_card or table.orders
    assert len(pkg.direct) > 0
    direct_ids = {d["node_id"] for d in pkg.direct}
    assert any("charge_card" in did or "orders" in did for did in direct_ids)

    # Constraints extraction
    assert len(pkg.constraints.parameter_constraints) > 0
    assert any("retry_count" in c for c in pkg.constraints.parameter_constraints)
    assert len(pkg.constraints.return_constraints) > 0
    assert any("bool" in c for c in pkg.constraints.return_constraints)
    assert len(pkg.constraints.exception_constraints) > 0
    assert any("CheckoutError" in c for c in pkg.constraints.exception_constraints)

    # Change plan
    assert pkg.change_plan is not None
    assert pkg.change_plan.risk_level in ("HIGH", "MEDIUM", "LOW")
    assert len(pkg.change_plan.steps) > 0

    # Token economics
    assert pkg.estimated_tokens > 0
    assert pkg.raw_file_tokens >= pkg.estimated_tokens
    assert pkg.token_reduction_pct >= 0.0


def test_progressive_disclosure_levels(tmp_path: Path):
    graph = _make_context_test_graph()
    db_file = tmp_path / "cache.db"
    build_sqlite_cache(graph, db_file)

    engine = GraphQueryEngine(graph, storage_dir=tmp_path)
    compiler = ContextCompiler(engine)

    pkg = compiler.compile("Fix process_checkout retry logic")

    # Level 1: brief
    md_l1 = pkg.to_markdown(level=1)
    # Level 2: standard
    md_l2 = pkg.to_markdown(level=2)
    # Level 3: full with snippets
    md_l3 = pkg.to_markdown(level=3)

    assert len(md_l1) < len(md_l2)
    assert "Extracted Code & Schema Constraints" not in md_l1
    assert "Extracted Code & Schema Constraints" in md_l2
    assert "Candidate Entrypoints" in md_l1
    assert "Evidence-Backed Blast Radius" in md_l2


def test_change_plan_generation(tmp_path: Path):
    graph = _make_context_test_graph()
    db_file = tmp_path / "cache.db"
    build_sqlite_cache(graph, db_file)

    engine = GraphQueryEngine(graph, storage_dir=tmp_path)
    plan: ChangePlan = engine.change_plan("Modify process_checkout")

    assert plan is not None
    assert len(plan.steps) >= 1
    # Because table.orders is written, risk should be assessed as HIGH
    assert plan.risk_level == "HIGH"
    assert any("schema" in r.lower() for r in plan.risk_reasons)

    plan_md = plan.to_markdown()
    assert "# Engineering Change Plan" in plan_md
    assert "Phase 2: Actionable Implementation Steps" in plan_md


def test_cli_context_flag(tmp_path: Path, capsys):
    from repopeek.cli import main
    from repopeek.storage import save_canonical_graph

    graph = _make_context_test_graph()
    repopeek_dir = tmp_path / ".repopeek"
    save_canonical_graph(graph, repopeek_dir)
    build_sqlite_cache(graph, repopeek_dir / "cache.db")

    ret = main([
        "--repo-path",
        str(tmp_path),
        "--context",
        "Fix process_checkout retry logic",
        "--level",
        "2",
    ])
    assert ret == 0

    captured = capsys.readouterr()
    assert "# RepoPeek Context Package" in captured.out
    assert "process_checkout" in captured.out
    assert "Blast Radius" in captured.out


def test_cli_plan_flag(tmp_path: Path, capsys):
    from repopeek.cli import main
    from repopeek.storage import save_canonical_graph

    graph = _make_context_test_graph()
    repopeek_dir = tmp_path / ".repopeek"
    save_canonical_graph(graph, repopeek_dir)
    build_sqlite_cache(graph, repopeek_dir / "cache.db")

    ret = main([
        "--repo-path",
        str(tmp_path),
        "--plan",
        "Update checkout transaction error handling",
    ])
    assert ret == 0

    captured = capsys.readouterr()
    assert "# Engineering Change Plan" in captured.out
    assert "Risk Level" in captured.out
