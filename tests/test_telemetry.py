"""Tests for MCP session-rollup telemetry and estimated savings."""

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
from repopeek.query.telemetry import TelemetrySession, build_session


# ---------------------------------------------------------------------------
# Pure accumulator math
# ---------------------------------------------------------------------------

def test_accumulator_sums_and_reduction_pct():
    """record_call accumulates totals and computes an estimated reduction pct."""
    s = TelemetrySession()
    s.record_call("repopeek_context", latency_ms=5.0, tokens_returned=1000,
                  tokens_saved_estimate=9000, files_avoided_estimate=4)
    s.record_call("repopeek_lookup", latency_ms=1.0, tokens_returned=80)

    assert s.total_calls == 2
    assert s.tokens_returned == 1080
    assert s.tokens_saved_estimate == 9000
    assert s.files_avoided_estimate == 4
    # baseline = returned + saved = 1080 + 9000 = 10080; 9000/10080 ~= 89.3%
    assert s.reduction_pct == pytest.approx(89.3, abs=0.1)


def test_per_tool_breakdown_and_avg_latency():
    """Per-tool counters track calls, tokens, and average latency."""
    s = TelemetrySession()
    s.record_call("repopeek_lookup", latency_ms=2.0, tokens_returned=50)
    s.record_call("repopeek_lookup", latency_ms=4.0, tokens_returned=70)

    d = s.to_dict()
    lookup = d["per_tool"]["repopeek_lookup"]
    assert lookup["calls"] == 2
    assert lookup["tokens_returned"] == 120
    assert lookup["avg_latency_ms"] == pytest.approx(3.0)


def test_reduction_pct_zero_when_no_savings():
    """No savings recorded yields a 0% reduction, never a divide-by-zero."""
    s = TelemetrySession()
    assert s.reduction_pct == 0.0
    s.record_call("repopeek_lookup", latency_ms=1.0, tokens_returned=80)
    assert s.reduction_pct == 0.0


def test_negative_values_clamped():
    """Negative savings/returns are clamped to zero (defensive)."""
    s = TelemetrySession()
    s.record_call("repopeek_context", latency_ms=1.0, tokens_returned=-5,
                  tokens_saved_estimate=-10, files_avoided_estimate=-2)
    assert s.tokens_returned == 0
    assert s.tokens_saved_estimate == 0
    assert s.files_avoided_estimate == 0


def test_pack_baseline_estimate():
    """Pack baseline models ~1200 tokens per avoided file."""
    assert TelemetrySession.estimate_pack_baseline_tokens(0) == 0
    assert TelemetrySession.estimate_pack_baseline_tokens(3) == 3600


def test_summary_line_mentions_estimate():
    """The one-liner is explicit that savings are an estimate."""
    s = TelemetrySession()
    s.record_call("repopeek_context", latency_ms=1.0, tokens_returned=500,
                  tokens_saved_estimate=4500, files_avoided_estimate=3)
    line = s.summary_line()
    assert "est." in line
    assert "tokens returned" in line


# ---------------------------------------------------------------------------
# Graceful no-OTel path
# ---------------------------------------------------------------------------

def test_build_session_without_otel_env(monkeypatch):
    """Default build (no env opt-in) produces a working, exporter-less session."""
    monkeypatch.delenv("REPOPEEK_OTEL", raising=False)
    monkeypatch.delenv("REPOPEEK_OTEL_ENDPOINT", raising=False)
    s = build_session()
    assert s._exporter is None
    # Still fully functional.
    s.record_call("repopeek_lookup", latency_ms=1.0, tokens_returned=80)
    assert s.total_calls == 1


def test_build_session_otel_requested_but_unavailable(monkeypatch):
    """Requesting OTel without the SDK degrades to the pure-Python path."""
    monkeypatch.setenv("REPOPEEK_OTEL", "1")
    monkeypatch.delenv("REPOPEEK_OTEL_ENDPOINT", raising=False)
    s = build_session()
    # Whether or not the SDK is installed, the session must still accumulate.
    s.record_call("repopeek_context", latency_ms=1.0, tokens_returned=100,
                  tokens_saved_estimate=900, files_avoided_estimate=1)
    assert s.total_calls == 1
    assert s.tokens_saved_estimate == 900


# ---------------------------------------------------------------------------
# End-to-end through the MCP server
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_graph() -> CanonicalGraph:
    graph = CanonicalGraph()
    n1 = NodeCard(
        id="py:auth.py:authenticate_user",
        kind="function",
        sig="def authenticate_user(token: str) -> bool",
        span=Span(file="auth.py", start=10, end=25),
        facts=NodeFacts(complexity=3, params=["token"], calls=1),
        story=NodeStory(text="Authenticates a user token", source="deterministic", confidence="high"),
        content_hash="h1",
    )
    n2 = NodeCard(
        id="py:routes.py:login_handler",
        kind="function",
        sig="def login_handler(req: dict) -> dict",
        span=Span(file="routes.py", start=5, end=15),
        facts=NodeFacts(complexity=2, params=["req"], calls=1),
        story=NodeStory(text="Login API endpoint", source="deterministic", confidence="high"),
        content_hash="h2",
    )
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_edge(Edge(src=n2.id, dst=n1.id, type=EdgeType.CALLS, confidence=Confidence.RESOLVED))
    return graph


def test_session_stats_tool_registered(sample_graph: CanonicalGraph):
    """The session_stats tool appears in tools/list."""
    server = RepoPeekMCPServer(GraphQueryEngine(graph=sample_graph))
    resp = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = {t["name"] for t in resp["result"]["tools"]}
    assert "repopeek_session_stats" in names


def test_tool_calls_are_recorded(sample_graph: CanonicalGraph):
    """Executing a tool increments the session accumulator."""
    server = RepoPeekMCPServer(GraphQueryEngine(graph=sample_graph))
    assert server.telemetry.total_calls == 0

    server.handle_request({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "repopeek_lookup", "arguments": {"query": "authenticate_user"}},
    })
    assert server.telemetry.total_calls == 1
    assert server.telemetry.tokens_returned > 0


def test_session_stats_does_not_count_itself(sample_graph: CanonicalGraph):
    """Reading the rollup must not inflate the rollup."""
    server = RepoPeekMCPServer(GraphQueryEngine(graph=sample_graph))
    server.handle_request({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "repopeek_lookup", "arguments": {"query": "authenticate_user"}},
    })
    calls_before = server.telemetry.total_calls

    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "repopeek_session_stats", "arguments": {"format": "json"}},
    })
    stats = json.loads(resp["result"]["content"][0]["text"])

    assert server.telemetry.total_calls == calls_before
    assert stats["total_tool_calls"] == calls_before
    assert "ESTIMATE" in stats["note"]


def test_context_call_estimates_savings(sample_graph: CanonicalGraph):
    """A context compile records a non-zero estimated savings from pack fields."""
    server = RepoPeekMCPServer(GraphQueryEngine(graph=sample_graph))
    server.handle_request({
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "repopeek_context", "arguments": {"task": "modify authenticate_user token check"}},
    })
    # The compiler guarantees a floor baseline (>=2000 raw tokens) and a compact
    # pack, so savings should be positive for any resolved task.
    assert server.telemetry.tokens_saved_estimate > 0
    assert server.telemetry.files_avoided_estimate >= 0
