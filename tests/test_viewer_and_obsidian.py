"""Tests for interactive Graph Viewer and Obsidian Vault Exporter/Reader."""

import json
import threading
import urllib.request
from http.server import HTTPServer
from pathlib import Path
import pytest

from repopeek.models.schema import (
    CanonicalGraph,
    Edge,
    EdgeType,
    NodeCard,
    NodeFacts,
    Span,
)
from repopeek.query.engine import GraphQueryEngine
from repopeek.storage.obsidian_exporter import export_to_obsidian_vault, read_obsidian_node
from repopeek.viewer.server import GraphViewerHandler, start_viewer
from repopeek.cli import main


@pytest.fixture
def sample_graph() -> CanonicalGraph:
    """Construct an interconnected test graph."""
    n1 = NodeCard(
        id="py:app/billing.py::process_invoice",
        kind="function",
        sig="def process_invoice(inv_id: str) -> bool",
        span=Span(file="app/billing.py", start=10, end=25),
        facts=NodeFacts(calls=2, complexity=3, reads=["table.invoices"], writes=["table.audit_log"]),
        content_hash="hash1",
    )
    n2 = NodeCard(
        id="py:app/billing.py::validate_tax",
        kind="function",
        sig="def validate_tax(amount: float) -> float",
        span=Span(file="app/billing.py", start=30, end=40),
        facts=NodeFacts(calls=0, complexity=1),
        content_hash="hash2",
    )
    n3 = NodeCard(
        id="table::invoices",
        kind="table",
        span=Span(file="db/schema.sql", start=1, end=15),
        content_hash="hash3",
    )
    e1 = Edge(src=n1.id, dst=n2.id, type=EdgeType.CALLS)
    e2 = Edge(src=n1.id, dst=n3.id, type=EdgeType.READS)

    return CanonicalGraph(
        nodes={n1.id: n1, n2.id: n2, n3.id: n3},
        edges=[e1, e2],
        repo_commit="abcdef123",
    )


def test_export_to_obsidian_vault(sample_graph: CanonicalGraph, tmp_path: Path):
    """Verify export creates valid Obsidian vault structure with wikilinks."""
    vault_dir = tmp_path / "obsidian_vault"
    res = export_to_obsidian_vault(sample_graph, vault_dir)

    assert vault_dir.exists()
    assert (vault_dir / ".obsidian" / "app.json").exists()
    assert (vault_dir / ".obsidian" / "graph.json").exists()
    assert (vault_dir / "00 Overview.md").exists()
    assert res["exported_notes"] == 3

    # Check categorized folders
    func_note = vault_dir / "Functions" / "process_invoice.md"
    assert func_note.exists()

    content = func_note.read_text(encoding="utf-8")
    assert "---" in content
    assert 'kind: "function"' in content
    assert "process_invoice" in content
    assert "[[validate_tax]]" in content
    assert "[[invoices]]" in content


def test_read_obsidian_node(sample_graph: CanonicalGraph, tmp_path: Path):
    """Verify reading documentation note from Obsidian vault."""
    vault_dir = tmp_path / "obsidian_vault"
    export_to_obsidian_vault(sample_graph, vault_dir)

    note = read_obsidian_node(vault_dir, "process_invoice")
    assert note is not None
    assert note["name"] == "process_invoice"
    assert "validate_tax" in note["wikilinks"]
    assert note["frontmatter"]["kind"] == "function"


def test_viewer_http_api(sample_graph: CanonicalGraph):
    """Verify local HTTP server endpoints for graph viewer."""
    engine = GraphQueryEngine(graph=sample_graph)
    server = start_viewer(engine, port=8799, open_browser=False)

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        # 1. Test index page
        with urllib.request.urlopen("http://127.0.0.1:8799/") as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "RepoPeek" in html
            assert "graph-canvas" in html

        # 2. Test /api/graph
        with urllib.request.urlopen("http://127.0.0.1:8799/api/graph?lens=all") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert len(data["nodes"]) == 3
            assert len(data["edges"]) == 2

        # 3. Test /api/impact
        with urllib.request.urlopen("http://127.0.0.1:8799/api/impact?target=process_invoice") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["found"] is True

        # 4. Test /api/pack
        with urllib.request.urlopen("http://127.0.0.1:8799/api/pack?target=process_invoice") as resp:
            assert resp.status == 200
            pack_text = resp.read().decode("utf-8")
            assert "Context Pack" in pack_text
    finally:
        server.shutdown()
        server.server_close()


def test_cli_export_and_read_obsidian(tmp_path: Path):
    """Verify CLI commands for Obsidian export and read."""
    fixture_repo = Path(__file__).parent / "fixtures" / "sample_repo"
    vault_target = tmp_path / "cli_vault"

    # Export
    exit_code = main(["--repo-path", str(fixture_repo), "--export-obsidian", str(vault_target)])
    assert exit_code == 0
    assert (vault_target / "00 Overview.md").exists()

    # Read
    exit_code = main(["--repo-path", str(fixture_repo), "--read-obsidian", "InvoiceParser", "--vault-path", str(vault_target)])
    assert exit_code == 0


def test_obsidian_vault_autodetect_and_open(tmp_path: Path, monkeypatch):
    """Verify system vault auto-detection and open dispatch."""
    from repopeek.storage import find_default_obsidian_vault, open_in_obsidian

    # Mock obsidian config
    fake_config = tmp_path / "obsidian.json"
    vault_target = tmp_path / "detected_vault"
    vault_target.mkdir()

    fake_config.write_text(json.dumps({
        "vaults": {
            "v1": {"path": str(vault_target), "open": True, "ts": 100}
        }
    }), encoding="utf-8")

    monkeypatch.setenv("APPDATA", str(tmp_path))
    (tmp_path / "obsidian").mkdir()
    (tmp_path / "obsidian" / "obsidian.json").write_text(fake_config.read_text())

    detected = find_default_obsidian_vault()
    assert detected == vault_target

    # Test open_in_obsidian with monkeypatched webbrowser
    opened_urls = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened_urls.append(url) or True)

    assert open_in_obsidian(vault_target) is True
    assert len(opened_urls) == 1
    assert "obsidian://open?path=" in opened_urls[0]

