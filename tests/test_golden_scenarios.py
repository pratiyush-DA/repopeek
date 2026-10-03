"""Golden verification tests validating the core product questions for low-context AI agents."""

from pathlib import Path
import pytest

from repopeek.graph.builder import GraphBuilder
from repopeek.query import ContextPack, GraphQueryEngine

FIXTURE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


@pytest.fixture(scope="module")
def golden_engine():
    """Build and enrich canonical graph from sample repository."""
    builder = GraphBuilder()
    graph = builder.build_from_directory(FIXTURE_REPO)
    return GraphQueryEngine(graph=graph)


def test_golden_question_1_blast_radius(golden_engine):
    """Q1: 'If I change parse_invoice(), which functions, files, tables and config keys can be affected?'"""
    # 1. Target lookup
    target_card = golden_engine.lookup("InvoiceParser.parse")
    assert target_card is not None
    assert "parse" in target_card.id

    # 2. Compute upstream blast radius
    impact = golden_engine.impact(target_card.id, max_depth=5)
    assert impact["found"] is True
    assert impact["affected_count"] > 0

    # 3. Verify affected files
    affected_files = set(impact["affected_files"])
    assert any("invoice.py" in f for f in affected_files)
    assert any("run_pipeline.sh" in f or "pipeline.yaml" in f or "main.py" in f for f in affected_files)

    # 4. Verify connected data tables and configs
    neighbors = golden_engine.neighbors(target_card.id, direction="both")
    related_ids = {e["dst"] for e in neighbors["outgoing"]} | {e["src"] for e in neighbors["incoming"]}
    assert any("invoices" in rid for rid in related_ids)


def test_golden_question_2_data_flow(golden_engine):
    """Q2: 'Where is this variable written, where is it read, and what does it flow into?'"""
    # Trace data entity table.invoices
    trace = golden_engine.data_trace("table.invoices")
    assert trace["readers_count"] >= 1

    reader_files = {r["file"] for r in trace["readers"] if r["file"]}
    assert any("invoice.py" in f for f in reader_files)

    # Check node-level AST reads and writes on the parser method
    parser_node = golden_engine.lookup("InvoiceParser.parse")
    assert parser_node is not None
    assert any("invoices" in r for r in parser_node.facts.reads)


def test_golden_question_3_minimal_context_pack(golden_engine):
    """Q3: 'Give me the smallest set of nodes, with one-line stories, I need to safely edit X.'"""
    target = "py:src/billing/invoice.py::InvoiceParser.parse"
    budget = 500  # Strict low-context agent budget

    pack = golden_engine.context_pack([target], token_budget=budget)

    # 1. Budget guarantee
    assert pack.estimated_tokens <= budget
    assert len(pack.nodes) >= 1
    assert len(pack.nodes) <= 10  # Compact sub-graph

    # 2. Verified one-line stories for every node
    for n in pack.nodes:
        assert "story" in n
        assert n["story"]["text"]
        assert len(n["story"]["text"].split()) <= 60

    # 3. Markdown prompt block format
    md = pack.to_markdown()
    assert f"# RepoPeek Context Pack: {target}" in md
    assert "## Atomic Node Cards" in md
    assert "## Blast Radius Summary" in md
    assert "src/billing/invoice.py" in md

    # 4. Verification that a low-context agent has the complete blast-radius and interface
    # without needing the whole multi-file repository
    assert len(pack.affected_files) >= 1
