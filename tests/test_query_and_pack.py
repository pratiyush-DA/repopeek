"""Tests for GraphQueryEngine, ContextPack generation, and MCP server protocol."""

import json
from pathlib import Path
import pytest

from repopeek.cli import main
from repopeek.graph.builder import GraphBuilder
from repopeek.query import ContextPack, GraphQueryEngine, RepoPeekMCPServer

FIXTURE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


@pytest.fixture(scope="module")
def sample_engine():
    """Build in-memory graph from sample repository and return initialized GraphQueryEngine."""
    builder = GraphBuilder()
    graph = builder.build_from_directory(FIXTURE_REPO)
    return GraphQueryEngine(graph=graph)


def test_engine_lookup(sample_engine):
    """Verify lookup by exact ID, qualified suffix, and table name."""
    # 1. Exact ID
    exact_id = "py:src/billing/invoice.py::InvoiceParser.parse"
    card = sample_engine.lookup(exact_id)
    assert card is not None
    assert card.id == exact_id
    assert card.kind == "method"

    # 2. Suffix match
    card_suffix = sample_engine.lookup("InvoiceParser.parse")
    assert card_suffix is not None
    assert card_suffix.id == exact_id

    # 3. Table entity lookup
    table_card = sample_engine.lookup("table.invoices")
    assert table_card is not None
    assert "invoices" in table_card.id

    # 4. Unknown query
    assert sample_engine.lookup("non_existent_symbol_12345") is None


def test_engine_neighbors(sample_engine):
    """Verify inspection of inbound and outbound relational edges."""
    target_id = "py:src/billing/invoice.py::InvoiceParser.parse"
    res = sample_engine.neighbors(target_id, direction="both")

    assert res["node"] is not None
    assert res["node"]["id"] == target_id

    # Outgoing edges should include embedded SQL and calls
    outgoing_types = {e["type"] for e in res["outgoing"]}
    assert "EMBEDS_SQL" in outgoing_types or "CALLS" in outgoing_types or "READS" in outgoing_types


def test_engine_impact_analysis(sample_engine):
    """Verify upstream blast-radius reachability for code and schema changes."""
    # Modifying table.invoices must impact the invoice parser
    res = sample_engine.impact("table.invoices", max_depth=4)

    assert res["found"] is True
    assert res["affected_count"] > 0
    assert any("invoice.py" in f for f in res["affected_files"])

    affected_ids = {n["id"] for n in res["affected_nodes"]}
    assert any("InvoiceParser" in aid or "parse" in aid for aid in affected_ids)


def test_engine_data_trace(sample_engine):
    """Verify data tracing finds readers and writers of data entities."""
    trace = sample_engine.data_trace("table.invoices")
    assert trace["readers_count"] > 0
    reader_ids = {r["reader_id"] for r in trace["readers"]}
    assert any("invoice.py" in rid for rid in reader_ids)


def test_context_pack_budget_and_markdown(sample_engine):
    """Verify ContextPack bundles minimal sufficient sub-graph within token budget."""
    target = "py:src/billing/invoice.py::InvoiceParser.parse"
    pack = sample_engine.context_pack([target], token_budget=800)

    assert isinstance(pack, ContextPack)
    assert pack.targets == [target]
    assert len(pack.nodes) >= 1
    assert pack.estimated_tokens <= 800

    md = pack.to_markdown()
    assert "# RepoPeek Context Pack" in md
    assert "InvoiceParser.parse" in md
    assert "Atomic Node Cards" in md

    # Check serialization
    d = pack.to_dict()
    assert d["nodes_count"] == len(pack.nodes)
    assert "src/billing/invoice.py" in d["affected_files"]


def test_mcp_server_protocol(sample_engine):
    """Verify JSON-RPC requests across initialize, tools/list, and tools/call."""
    server = RepoPeekMCPServer(sample_engine)

    # 1. initialize
    init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    init_resp = server.handle_request(init_req)
    assert init_resp["id"] == 1
    assert init_resp["result"]["serverInfo"]["name"] == "repopeek-mcp"

    # 2. tools/list
    list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    list_resp = server.handle_request(list_req)
    assert list_resp["id"] == 2
    tool_names = {t["name"] for t in list_resp["result"]["tools"]}
    assert "repopeek_lookup" in tool_names
    assert "repopeek_impact" in tool_names
    assert "repopeek_context_pack" in tool_names

    # 3. tools/call lookup
    call_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "repopeek_lookup", "arguments": {"query": "InvoiceParser.parse"}},
    }
    call_resp = server.handle_request(call_req)
    assert call_resp["id"] == 3
    content_text = call_resp["result"]["content"][0]["text"]
    assert "InvoiceParser.parse" in content_text

    # 4. tools/call impact
    impact_req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "repopeek_impact", "arguments": {"target": "table.invoices"}},
    }
    impact_resp = server.handle_request(impact_req)
    assert impact_resp["id"] == 4
    impact_text = impact_resp["result"]["content"][0]["text"]
    assert "invoice.py" in impact_text

    # 5. tools/call context_pack
    pack_req = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "repopeek_context_pack",
            "arguments": {"targets": ["InvoiceParser.parse"], "token_budget": 500},
        },
    }
    pack_resp = server.handle_request(pack_req)
    assert pack_resp["id"] == 5
    pack_text = pack_resp["result"]["content"][0]["text"]
    assert "# RepoPeek Context Pack" in pack_text


def test_cli_query_flags(capsys):
    """Verify CLI flags --lookup, --impact, and --pack execute queries."""
    # Test --lookup
    code_lookup = main(["--repo-path", str(FIXTURE_REPO), "--lookup", "InvoiceParser.parse"])
    assert code_lookup == 0
    captured = capsys.readouterr()
    assert "InvoiceParser.parse" in captured.out

    # Test --impact
    code_impact = main(["--repo-path", str(FIXTURE_REPO), "--impact", "table.invoices"])
    assert code_impact == 0
    captured_impact = capsys.readouterr()
    assert "affected_count" in captured_impact.out

    # Test --pack
    code_pack = main(["--repo-path", str(FIXTURE_REPO), "--pack", "InvoiceParser.parse"])
    assert code_pack == 0
    captured_pack = capsys.readouterr()
    assert "# RepoPeek Context Pack" in captured_pack.out
