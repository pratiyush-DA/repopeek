"""Tests for Agent MCP Suite."""

import json
from pathlib import Path
import pytest

from repopeek.models.schema import (
    CanonicalGraph,
    Confidence,
    Edge,
    EdgeType,
    NodeCard,
    NodeFacts,
    NodeStory,
    Span,
)
from repopeek.query.engine import GraphQueryEngine
from repopeek.query.mcp_server import RepoPeekMCPServer


@pytest.fixture
def sample_graph(tmp_path: Path) -> CanonicalGraph:
    """Create a sample canonical graph for MCP server testing."""
    graph = CanonicalGraph()

    # Node 1: function authenticate_user
    n1 = NodeCard(
        id="py:auth.py:authenticate_user",
        kind="function",
        sig="def authenticate_user(token: str) -> bool",
        span=Span(file="auth.py", start=10, end=25),
        facts=NodeFacts(complexity=3, params=["token"], calls=1, reads=["ROUTE:POST:/api/auth/login"]),
        story=NodeStory(text="Authenticates user token against auth provider", source="deterministic", confidence="high"),
        content_hash="mock_hash_auth",
    )
    # Node 2: function login_handler
    n2 = NodeCard(
        id="py:routes.py:login_handler",
        kind="function",
        sig="def login_handler(req: dict) -> dict",
        span=Span(file="routes.py", start=5, end=15),
        facts=NodeFacts(complexity=2, params=["req"], calls=1, reads=["ROUTE:POST:/api/auth/login"]),
        story=NodeStory(text="API endpoint for user login", source="deterministic", confidence="high"),
        content_hash="mock_hash_routes",
    )
    # Node 3: table users
    n3 = NodeCard(
        id="sql:schema.sql:users",
        kind="sql_table",
        sig="CREATE TABLE users (id INT PRIMARY KEY, token TEXT)",
        span=Span(file="schema.sql", start=1, end=5),
        facts=NodeFacts(),
        story=NodeStory(text="User account storage table", source="deterministic", confidence="high"),
        content_hash="mock_hash_sql",
    )

    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)

    graph.add_edge(
        Edge(src=n2.id, dst=n1.id, type=EdgeType.CALLS, confidence=Confidence.RESOLVED)
    )
    graph.add_edge(
        Edge(src=n1.id, dst=n3.id, type=EdgeType.READS, confidence=Confidence.RESOLVED)
    )

    return graph


def test_mcp_initialize_and_tools_list(sample_graph: CanonicalGraph):
    """Test MCP protocol initialize handshake and tool registration."""
    engine = GraphQueryEngine(graph=sample_graph)
    server = RepoPeekMCPServer(engine)

    init_resp = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert init_resp["result"]["serverInfo"]["name"] == "repopeek-mcp"

    list_resp = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tool_names = {t["name"] for t in list_resp["result"]["tools"]}

    expected_tools = {
        "repopeek_context",
        "repopeek_plan",
        "repopeek_impact",
        "repopeek_routes",
        "repopeek_co_changes",
        "repopeek_resolve",
        "repopeek_lookup",
        "repopeek_neighbors",
        "repopeek_data_trace",
        "repopeek_context_pack",
    }
    assert expected_tools.issubset(tool_names)


def test_mcp_tool_execution(sample_graph: CanonicalGraph):
    """Test executing tools via tools/call dispatch."""
    engine = GraphQueryEngine(graph=sample_graph)
    server = RepoPeekMCPServer(engine)

    # 1. repopeek_lookup
    resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {"name": "repopeek_lookup", "arguments": {"query": "authenticate_user"}},
    })
    content = resp["result"]["content"][0]["text"]
    assert "authenticate_user" in content

    # 2. repopeek_impact
    resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {"name": "repopeek_impact", "arguments": {"target": "authenticate_user"}},
    })
    impact_data = json.loads(resp["result"]["content"][0]["text"])
    assert "direct" in impact_data or "affected_nodes" in impact_data

    # 3. repopeek_routes
    resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {"name": "repopeek_routes", "arguments": {}},
    })
    routes_data = json.loads(resp["result"]["content"][0]["text"])
    assert "total_routes" in routes_data
    assert routes_data["total_routes"] >= 1

    # 4. repopeek_context (markdown)
    resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 13,
        "method": "tools/call",
        "params": {"name": "repopeek_context", "arguments": {"task": "authenticate user token", "level": 1}},
    })
    assert "Context Package" in resp["result"]["content"][0]["text"]

    # 5. repopeek_context (json)
    resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 14,
        "method": "tools/call",
        "params": {"name": "repopeek_context", "arguments": {"task": "authenticate user token", "format": "json"}},
    })
    ctx_json = json.loads(resp["result"]["content"][0]["text"])
    assert "task" in ctx_json

    # 6. repopeek_plan
    resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 15,
        "method": "tools/call",
        "params": {"name": "repopeek_plan", "arguments": {"task": "update authentication"}},
    })
    assert "Change Plan" in resp["result"]["content"][0]["text"]

    # 7. repopeek_data_trace
    resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 16,
        "method": "tools/call",
        "params": {"name": "repopeek_data_trace", "arguments": {"entity": "users"}},
    })
    trace_data = json.loads(resp["result"]["content"][0]["text"])
    assert "entity" in trace_data

    # 8. Unknown tool returns JSON-RPC error
    err_resp = server.handle_request({
        "jsonrpc": "2.0",
        "id": 99,
        "method": "tools/call",
        "params": {"name": "unknown_tool", "arguments": {}},
    })
    assert "error" in err_resp
    assert err_resp["error"]["code"] == -32601
