"""Tests for task intent resolution, identifier extraction, FTS5 BM25, and RRF."""

import json
from pathlib import Path
import pytest

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
from repopeek.retrieval.intent import (
    TaskIntent,
    _build_fts_query,
    extract_task_identifiers,
    generate_identifier_variants,
    normalize_task_text,
    reciprocal_rank_fusion,
    resolve_task_to_symbols,
)
from repopeek.storage.sqlite_cache import (
    build_sqlite_cache,
    query_fts5_bm25,
    update_sqlite_file,
)


def _make_sample_graph() -> CanonicalGraph:
    """Helper to build a sample graph for retrieval tests."""
    graph = CanonicalGraph(
        schema_version="1.0.0",
        tool_version="0.1.0",
        repo_commit="c0ffee",
        dirty=False,
    )

    n1 = NodeCard(
        id="python:billing/processor.py::PaymentProcessor",
        kind="class",
        sig="class PaymentProcessor",
        span=Span(file="billing/processor.py", start=10, end=80),
        facts=NodeFacts(complexity=5),
        story=NodeStory(text="Handles customer payment processing and gateway communication"),
        content_hash="hash_p1",
    )
    n2 = NodeCard(
        id="python:billing/processor.py::PaymentProcessor.process_payment",
        kind="method",
        sig="def process_payment(self, amount: float, retry_count: int = 3) -> bool",
        span=Span(file="billing/processor.py", start=25, end=50),
        facts=NodeFacts(calls=2, params=["self", "amount", "retry_count"], returns="bool"),
        story=NodeStory(text="Processes credit card transaction with retry logic"),
        content_hash="hash_p2",
    )
    n3 = NodeCard(
        id="python:billing/tax.py::calculate_tax",
        kind="function",
        sig="def calculate_tax(amount: float, jurisdiction: str) -> float",
        span=Span(file="billing/tax.py", start=5, end=20),
        facts=NodeFacts(calls=0, params=["amount", "jurisdiction"], returns="float"),
        story=NodeStory(text="Calculates regional tax based on customer jurisdiction"),
        content_hash="hash_t1",
    )
    n4 = NodeCard(
        id="python:auth/tokens.py::verify_jwt",
        kind="function",
        sig="def verify_jwt(token: str) -> dict",
        span=Span(file="auth/tokens.py", start=1, end=15),
        facts=NodeFacts(calls=1, params=["token"], returns="dict"),
        story=NodeStory(text="Validates incoming auth JWT token and claims"),
        content_hash="hash_a1",
    )

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)
    graph.add_node(n4)

    graph.add_edge(
        Edge(
            src=n2.id,
            dst=n3.id,
            type=EdgeType.CALLS,
            confidence=Confidence.RESOLVED,
            evidence=Evidence(
                file="billing/processor.py",
                start_line=30,
                end_line=30,
                how_derived="ast:call",
            ),
        )
    )
    return graph


def test_normalize_task_text():
    raw = "Fix the `retry_count` in PaymentProcessor.process_payment   for 401 error!"
    normalized = normalize_task_text(raw)
    assert "retry_count" in normalized
    assert "PaymentProcessor.process_payment" in normalized
    assert "  " not in normalized


def test_extract_task_identifiers():
    task = "Update `process_payment` in billing.PaymentProcessor to handle 'tax_rate' and retryCount"
    intent = extract_task_identifiers(task)

    assert isinstance(intent, TaskIntent)
    assert "process_payment" in intent.quoted_names or "process_payment" in intent.identifiers
    assert "billing.PaymentProcessor" in intent.dotted_names or "billing.PaymentProcessor" in intent.identifiers
    assert "retryCount" in intent.identifiers

    # Check action verbs are filtered from identifiers
    assert "update" not in intent.identifiers
    assert "handle" not in intent.identifiers
    assert "update" in intent.verbs
    assert "handle" in intent.verbs


def test_generate_identifier_variants():
    variants_camel = generate_identifier_variants("paymentRetryCount")
    assert "paymentRetryCount" in variants_camel
    assert "payment_retry_count" in variants_camel
    assert "retryCount" in variants_camel or "payment" in variants_camel

    variants_snake = generate_identifier_variants("calculate_total_tax")
    assert "calculate_total_tax" in variants_snake
    assert "calculateTotalTax" in variants_snake


def test_reciprocal_rank_fusion():
    list1 = [("node_a", 10.0), ("node_b", 5.0), ("node_c", 2.0)]
    list2 = [("node_b", 100.0), ("node_a", 50.0), ("node_d", 20.0)]

    fused = reciprocal_rank_fusion(list1, list2, k=60)
    assert len(fused) == 4
    # Both node_a and node_b are in top 2 across both lists, so they should rank higher than node_c and node_d
    fused_ids = [item[0] for item in fused]
    assert set(fused_ids[:2]) == {"node_a", "node_b"}
    assert set(fused_ids[2:]) == {"node_c", "node_d"}

    # Test with custom weights
    fused_weighted = reciprocal_rank_fusion(list1, list2, k=60, weights=[2.0, 0.5])
    assert fused_weighted[0][0] == "node_a"  # list1 top item heavily prioritized


def test_sqlite_fts5_bm25_search(tmp_path: Path):
    graph = _make_sample_graph()
    db_file = tmp_path / "cache.db"

    build_sqlite_cache(graph, db_file)
    assert db_file.exists()

    # Query by symbol name
    results = query_fts5_bm25(db_file, "PaymentProcessor", limit=10)
    assert len(results) > 0
    hit_ids = [r[0] for r in results]
    assert "python:billing/processor.py::PaymentProcessor" in hit_ids

    # Query by story content
    results_story = query_fts5_bm25(db_file, "credit card transaction", limit=10)
    assert len(results_story) > 0
    assert results_story[0][0] == "python:billing/processor.py::PaymentProcessor.process_payment"

    # Query with empty or whitespace string returns empty list
    assert query_fts5_bm25(db_file, "") == []
    assert query_fts5_bm25(db_file, "   ") == []


def test_sqlite_fts5_incremental_update(tmp_path: Path):
    graph = _make_sample_graph()
    db_file = tmp_path / "cache.db"
    build_sqlite_cache(graph, db_file)

    # Initial search for tax
    initial = query_fts5_bm25(db_file, "calculate_tax")
    assert any("calculate_tax" in r[0] for r in initial)

    # Mutate calculate_tax to compute_vat in graph
    del graph.nodes["python:billing/tax.py::calculate_tax"]
    new_tax_node = NodeCard(
        id="python:billing/tax.py::compute_vat",
        kind="function",
        sig="def compute_vat(amount: float) -> float",
        span=Span(file="billing/tax.py", start=5, end=20),
        facts=NodeFacts(calls=0),
        story=NodeStory(text="Computes VAT for billing transactions"),
        content_hash="hash_vat",
    )
    graph.nodes[new_tax_node.id] = new_tax_node

    # Update SQLite cache incrementally for billing/tax.py
    update_sqlite_file("billing/tax.py", graph, db_file)

    # Old symbol should be gone from FTS5
    old_res = query_fts5_bm25(db_file, "calculate_tax")
    assert not any("calculate_tax" in r[0] for r in old_res)

    # New symbol should be present in FTS5
    new_res = query_fts5_bm25(db_file, "compute_vat")
    assert any("compute_vat" in r[0] for r in new_res)


def test_resolve_task_to_symbols():
    graph = _make_sample_graph()
    engine = GraphQueryEngine(graph)
    node_index = engine._build_node_index()

    candidates = resolve_task_to_symbols(
        task="Fix the retry logic in PaymentProcessor.process_payment",
        node_index=node_index,
        fts_results=None,
        limit=5,
    )

    assert len(candidates) > 0
    top_candidate = candidates[0]
    assert "process_payment" in top_candidate.node_id or "PaymentProcessor" in top_candidate.node_id
    assert top_candidate.score > 0
    assert len(top_candidate.reasons) > 0


def test_graph_query_engine_resolve_task(tmp_path: Path):
    graph = _make_sample_graph()
    db_file = tmp_path / "cache.db"
    build_sqlite_cache(graph, db_file)

    engine = GraphQueryEngine(graph, storage_dir=tmp_path)
    results = engine.resolve_task("Change tax calculation jurisdiction handling", limit=5)

    assert len(results) > 0
    # Top result should be the calculate_tax node
    assert results[0]["node_id"] == "python:billing/tax.py::calculate_tax"
    assert results[0]["kind"] == "function"
    assert "calculate_tax" in results[0]["sig"]
    assert results[0]["file"] == "billing/tax.py"
    assert results[0]["score"] > 0
    assert len(results[0]["reasons"]) > 0


def test_cli_resolve_flag(tmp_path: Path, capsys):
    from repopeek.cli import main
    from repopeek.storage import save_canonical_graph

    graph = _make_sample_graph()
    repopeek_dir = tmp_path / ".repopeek"
    save_canonical_graph(graph, repopeek_dir)
    build_sqlite_cache(graph, repopeek_dir / "cache.db")

    ret = main([
        "--repo-path",
        str(tmp_path),
        "--resolve",
        "Fix verify_jwt auth token verification",
    ])
    assert ret == 0

    captured = capsys.readouterr()
    output_json = json.loads(captured.out)
    assert isinstance(output_json, list)
    assert len(output_json) > 0
    assert any("verify_jwt" in c["node_id"] for c in output_json)
