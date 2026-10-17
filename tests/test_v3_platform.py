"""Tests for RepoPeek V3 Platform: MCP Installer, Live Viewer REST APIs, Notion Sync, and Multi-Root Federation."""

import json
from pathlib import Path
import urllib.request
import pytest

from repopeek import __version__
from repopeek.cli import main
from repopeek.export.notion_sync import format_notion_markdown_summary, generate_notion_sync_payload
from repopeek.graph.builder import GraphBuilder
from repopeek.mcp_installer import (
    generate_repopeek_mcp_entry,
    get_default_config_path,
    install_all_clients,
    install_mcp_config,
)
from repopeek.models.schema import (
    CanonicalGraph,
    Edge,
    EdgeType,
    NodeCard,
    NodeFacts,
    Span,
)
from repopeek.query.engine import GraphQueryEngine
from repopeek.viewer.server import start_viewer


@pytest.fixture
def v3_test_graph() -> CanonicalGraph:
    n1 = NodeCard(
        id="py:backend/api.py::create_order",
        kind="function",
        sig="def create_order(user_id: str, item_id: str)",
        span=Span(file="backend/api.py", start=1, end=20),
        facts=NodeFacts(calls=1, complexity=2),
        content_hash="h1",
    )
    n2 = NodeCard(
        id="py:backend/db.py::orders_table",
        kind="table",
        sig="table orders",
        span=Span(file="backend/db.py", start=1, end=10),
        content_hash="h2",
    )
    n3 = NodeCard(
        id="ts:frontend/client.ts::submitOrder",
        kind="function",
        sig="export async function submitOrder()",
        span=Span(file="frontend/client.ts", start=5, end=15),
        content_hash="h3",
    )
    e1 = Edge(src=n1.id, dst=n2.id, type=EdgeType.WRITES)
    e2 = Edge(src=n3.id, dst=n1.id, type=EdgeType.INVOKES)
    return CanonicalGraph(
        nodes={n1.id: n1, n2.id: n2, n3.id: n3},
        edges=[e1, e2],
    )


def test_version_bump():
    assert __version__ == "0.3.0"


def test_mcp_installer_create_and_backup(tmp_path: Path):
    config_file = tmp_path / "mcp.json"
    repo_path = tmp_path / "my_project"
    repo_path.mkdir()

    # Initial install
    res = install_mcp_config("cursor", repo_path=repo_path, target_file=config_file)
    assert res["status"] == "success"
    assert config_file.exists()

    data = json.loads(config_file.read_text(encoding="utf-8"))
    assert "mcpServers" in data
    assert "repopeek" in data["mcpServers"]
    entry = data["mcpServers"]["repopeek"]
    assert entry["command"] == "repopeek"
    assert "--serve-mcp" in entry["args"]
    assert str(repo_path.resolve()) in entry["args"]

    # Re-run with backup
    res2 = install_mcp_config("cursor", repo_path=repo_path, target_file=config_file, backup=True)
    assert res2["status"] == "success"
    assert res2["backup"] is not None
    assert Path(res2["backup"]).exists()


def test_mcp_installer_entry_generation(tmp_path: Path):
    entry = generate_repopeek_mcp_entry(tmp_path, use_python_exec=True)
    assert entry["command"].endswith(".exe") or "python" in entry["command"]
    assert "-m" in entry["args"]
    assert "repopeek" in entry["args"]


def test_generate_repopeek_system_prompt():
    from repopeek.mcp_installer import generate_repopeek_system_prompt
    general = generate_repopeek_system_prompt("general")
    assert "RepoPeek Code Intelligence Protocol" in general
    assert "Hybrid Decision Ladder" in general
    assert "repopeek_context" in general
    assert "repopeek_lookup" in general
    assert "repopeek_impact" in general
    assert "Leaf / Single-File Edit" in general

    cursor = generate_repopeek_system_prompt("cursor")
    assert "alwaysApply: true" in cursor
    assert "globs: *" in cursor


def test_install_agent_rules_idempotent(tmp_path: Path):
    from repopeek.mcp_installer import (
        START_RULE_TAG,
        END_RULE_TAG,
        install_agent_rules,
        install_all_rules,
    )
    repo_dir = tmp_path / "sample_repo"
    repo_dir.mkdir()

    # 1. New rule file installation
    res = install_agent_rules("claude", repo_path=repo_dir)
    assert res["status"] == "success"
    claude_md = repo_dir / "CLAUDE.md"
    assert claude_md.exists()
    assert START_RULE_TAG in claude_md.read_text(encoding="utf-8")

    # 2. Existing file with user custom instructions - must not be clobbered
    custom_md = repo_dir / "CUSTOM.md"
    custom_md.write_text("# My Project Instructions\nAlways run tests.", encoding="utf-8")
    res_custom = install_agent_rules("general", repo_path=repo_dir, rule_files=[custom_md])
    assert res_custom["status"] == "success"
    content = custom_md.read_text(encoding="utf-8")
    assert "# My Project Instructions" in content
    assert "Always run tests." in content
    assert START_RULE_TAG in content

    # 3. Idempotent re-run - replaces block without duplicating
    res_re = install_agent_rules("general", repo_path=repo_dir, rule_files=[custom_md])
    assert res_re["status"] == "success"
    content_re = custom_md.read_text(encoding="utf-8")
    assert content_re.count(START_RULE_TAG) == 1
    assert content_re.count(END_RULE_TAG) == 1
    assert "# My Project Instructions" in content_re

    # 4. Install all rules
    all_res = install_all_rules(repo_path=repo_dir)
    assert "cursor" in all_res
    assert "claude" in all_res
    assert "agents" in all_res
    assert (repo_dir / "AGENTS.md").exists()
    assert (repo_dir / ".cursor" / "rules" / "repopeek.mdc").exists()


def test_viewer_v3_rest_endpoints(v3_test_graph: CanonicalGraph):
    import threading
    engine = GraphQueryEngine(graph=v3_test_graph)
    server = start_viewer(engine, port=8877, open_browser=False)

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        base_url = "http://127.0.0.1:8877"

        # 1. HTML index
        with urllib.request.urlopen(f"{base_url}/") as resp:
            assert resp.status == 200
            html = resp.read().decode("utf-8")
            assert "<canvas" in html
            assert "RepoPeek" in html

        # 2. Graph API
        with urllib.request.urlopen(f"{base_url}/api/graph") as resp:
            assert resp.status == 200
            graph_data = json.loads(resp.read().decode("utf-8"))
            assert len(graph_data["nodes"]) == 3
            assert len(graph_data["edges"]) == 2

        # 3. God nodes API
        with urllib.request.urlopen(f"{base_url}/api/god-nodes?top_n=5") as resp:
            assert resp.status == 200
            god_data = json.loads(resp.read().decode("utf-8"))
            assert isinstance(god_data, list)
            assert len(god_data) >= 1

        # 4. Cycles API
        with urllib.request.urlopen(f"{base_url}/api/cycles") as resp:
            assert resp.status == 200
            cycles_data = json.loads(resp.read().decode("utf-8"))
            assert "cycles" in cycles_data

        # 5. Communities API
        with urllib.request.urlopen(f"{base_url}/api/communities") as resp:
            assert resp.status == 200
            comm_data = json.loads(resp.read().decode("utf-8"))
            assert "communities" in comm_data
            assert "labels" in comm_data
    finally:
        server.shutdown()
        server.server_close()


def test_notion_sync_payload(v3_test_graph: CanonicalGraph):
    payload = generate_notion_sync_payload(graph=v3_test_graph, roi_token_reduction_pct=82.5)
    assert payload["version"] == "0.3.0"
    assert payload["node_count"] == 3
    assert payload["edge_count"] == 2
    assert "py" in payload["languages_detected"]
    assert "ts" in payload["languages_detected"]

    summary_md = format_notion_markdown_summary(payload)
    assert "RepoPeek v0.3.0 Live Metrics" in summary_md
    assert "82.5% context savings" in summary_md


def test_build_from_directories(tmp_path: Path):
    d1 = tmp_path / "frontend"
    d2 = tmp_path / "backend"
    d1.mkdir()
    d2.mkdir()

    (d1 / "index.ts").write_text("export function runUi() { return 1; }\n", encoding="utf-8")
    (d2 / "server.py").write_text("def run_server(): pass\n", encoding="utf-8")

    builder = GraphBuilder()
    graph = builder.build_from_directories([d1, d2])
    assert len(graph.nodes) >= 2


def test_cli_mcp_install(tmp_path: Path):
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    # Test mcp install CLI alias
    code = main(["mcp", "install", "cursor", "--repo-path", str(repo_dir)])
    assert code == 0
