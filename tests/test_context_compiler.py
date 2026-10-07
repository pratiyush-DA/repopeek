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


def _make_padding_graph() -> CanonicalGraph:
    """A strongly-matched entrypoint plus a low-signal blast-only neighbor in another file."""
    graph = CanonicalGraph(schema_version="1.0.0", tool_version="0.1.0", repo_commit="pad", dirty=False)
    top = NodeCard(
        id="python:billing/checkout.py::process_checkout",
        kind="function",
        sig="def process_checkout(cart_id: str, retry_count: int = 3) -> bool",
        span=Span(file="billing/checkout.py", start=10, end=40),
        facts=NodeFacts(params=["cart_id", "retry_count"], returns="bool"),
        story=NodeStory(text="Processes checkout with retry_count budget"),
        content_hash="t1",
    )
    pad = NodeCard(
        id="python:infra/audit.py::write_audit_log",
        kind="function",
        sig="def write_audit_log(event) -> None",
        span=Span(file="infra/audit.py", start=3, end=20),
        facts=NodeFacts(params=["event"]),
        story=NodeStory(text="Persists an audit trail entry"),
        content_hash="t2",
    )
    graph.add_node(top)
    graph.add_node(pad)
    graph.add_edge(Edge(
        src=top.id, dst=pad.id, type=EdgeType.CALLS, confidence=Confidence.RESOLVED,
        evidence=Evidence(file="billing/checkout.py", start_line=30, end_line=30, how_derived="ast:call"),
    ))
    return graph


def test_file_precision_trims_low_signal_padding(tmp_path: Path):
    """A blast-only neighbor whose file is far below the top score is trimmed (precision)."""
    graph = _make_padding_graph()
    build_sqlite_cache(graph, tmp_path / "cache.db")
    engine = GraphQueryEngine(graph, storage_dir=tmp_path)

    pkg = engine.compile_context("Update retry_count in process_checkout", budget=1500, level=2)
    files = {f.replace("\\", "/") for f in pkg.affected_files}

    assert "billing/checkout.py" in files          # matched entrypoint file is kept
    assert "infra/audit.py" not in files           # low-signal padding neighbor is trimmed


def test_token_budget_trims_snippets_but_keeps_primary(tmp_path: Path):
    """When the rendered pack exceeds budget, snippets are shed but the primary stays."""
    svc = tmp_path / "svc"
    svc.mkdir()
    body = "\n".join(f"    x{i} = compute({i})" for i in range(45))
    for name in ("alpha", "beta", "gamma"):
        (svc / f"{name}.py").write_text(
            f"def {name}_handler(payload):\n{body}\n    return payload\n", encoding="utf-8"
        )

    graph = CanonicalGraph(schema_version="1.0.0", tool_version="0.1.0", repo_commit="b", dirty=False)
    ids = []
    for i, name in enumerate(("alpha", "beta", "gamma")):
        nid = f"python:svc/{name}.py::{name}_handler"
        ids.append(nid)
        graph.add_node(NodeCard(
            id=nid, kind="function", sig=f"def {name}_handler(payload)",
            span=Span(file=f"svc/{name}.py", start=1, end=47),
            facts=NodeFacts(params=["payload"]),
            story=NodeStory(text=f"{name} handler for payload"),
            content_hash=f"h{i}",
        ))
    graph.add_edge(Edge(src=ids[0], dst=ids[1], type=EdgeType.CALLS, confidence=Confidence.RESOLVED,
                        evidence=Evidence(file="svc/alpha.py", start_line=1, end_line=1, how_derived="ast")))
    graph.add_edge(Edge(src=ids[1], dst=ids[2], type=EdgeType.CALLS, confidence=Confidence.RESOLVED,
                        evidence=Evidence(file="svc/beta.py", start_line=1, end_line=1, how_derived="ast")))

    build_sqlite_cache(graph, tmp_path / "cache.db")
    engine = GraphQueryEngine(graph, storage_dir=tmp_path, repo_root=tmp_path)

    task = "update alpha_handler beta_handler gamma_handler payload"
    big = engine.compile_context(task, budget=5000, level=2)
    small = engine.compile_context(task, budget=600, level=2)

    # Budget enforcement trimmed snippet material relative to the unconstrained pack.
    assert small.estimated_tokens < big.estimated_tokens
    assert len(small.snippets) < len(big.snippets)
    # The primary entrypoint and at least one snippet survive the trim.
    assert small.entrypoints
    assert len(small.snippets) >= 1
