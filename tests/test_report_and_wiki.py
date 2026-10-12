"""Tests for rich graph reporting, agent wiki export, and HTML visualizer."""

import tempfile
from pathlib import Path
import pytest

from repopeek.export.html import export_html
from repopeek.export.report import generate_graph_report
from repopeek.export.wiki import export_wiki
from repopeek.models.schema import CanonicalGraph, Edge, EdgeType, NodeCard, NodeFacts, Span


def _build_sample_graph() -> CanonicalGraph:
    graph = CanonicalGraph()
    n1 = NodeCard(
        id="py:app/main.py::MainApp",
        kind="class",
        sig="MainApp",
        span=Span(file="app/main.py", start=1, end=50),
        facts=NodeFacts(complexity=5),
        content_hash="h1",
    )
    n2 = NodeCard(
        id="py:app/helper.py::help_func",
        kind="function",
        sig="help_func()",
        span=Span(file="app/helper.py", start=10, end=30),
        facts=NodeFacts(complexity=2),
        content_hash="h2",
    )
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_edge(Edge(src=n1.id, dst=n2.id, type=EdgeType.CALLS))
    return graph


def test_generate_graph_report():
    graph = _build_sample_graph()
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = Path(tmpdir) / "GRAPH_REPORT.md"
        report_text = generate_graph_report(graph, project_name="SampleProject", out_path=report_path)

        assert report_path.exists()
        assert "# Knowledge Graph Audit Report — SampleProject" in report_text
        assert "## Executive Summary" in report_text
        assert "## Top God Nodes" in report_text
        assert "## Modular Communities" in report_text
        assert "## Suggested Architectural Questions" in report_text
        assert "MainApp" in report_text


def test_export_wiki():
    graph = _build_sample_graph()
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_dir = Path(tmpdir) / "wiki"
        count = export_wiki(graph, out_dir=wiki_dir)

        assert count > 0
        assert (wiki_dir / "index.md").exists()
        index_content = (wiki_dir / "index.md").read_text(encoding="utf-8")
        assert "# Repository Architecture Wiki" in index_content
        assert "## Summary Metrics" in index_content
        assert "## Functional Communities" in index_content

        # At least one community file should exist
        comm_files = list(wiki_dir.glob("community_*.md"))
        assert len(comm_files) > 0


def test_export_html():
    graph = _build_sample_graph()
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "graph.html"
        res = export_html(graph, out_file=html_path)

        assert html_path.exists()
        content = html_path.read_text(encoding="utf-8")
        assert "<title>RepoPeek Knowledge Graph</title>" in content
        assert "vis.Network" in content
        assert "MainApp" in content
