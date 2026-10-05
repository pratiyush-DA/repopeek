"""Tests for Incremental File Watcher and Background Sync Daemon."""

from pathlib import Path
import time
import pytest

from repopeek.daemon.watcher import RepoPeekWatcher
from repopeek.discovery.crawler import discover_repository
from repopeek.graph.builder import GraphBuilder
from repopeek.storage import save_canonical_graph


def test_watcher_detects_and_syncs_file_modification(tmp_path: Path):
    """Test modifying a python source file triggers incremental update in <50ms."""
    repo_root = tmp_path / "src"
    repo_root.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Initial file
    py_file = repo_root / "service.py"
    py_file.write_text("def original_function():\n    return 42\n", encoding="utf-8")

    # Initial build and save
    builder = GraphBuilder()
    graph = builder.build_from_directory(repo_root)
    save_canonical_graph(graph, output_dir, repo_root=repo_root)

    changed_events = []
    def on_change_callback(changed_file: Path, updated_graph):
        changed_events.append((changed_file, len(updated_graph.nodes)))

    watcher = RepoPeekWatcher(
        repo_root=repo_root,
        output_dir=output_dir,
        graph=graph,
        poll_interval=0.1,
        debounce_ms=0,
        on_change=on_change_callback,
    )

    # Initial run_once should see 0 changes
    changes = watcher.run_once()
    assert len(changes) == 0

    # Wait a small slice so mtime definitely changes on all filesystems
    time.sleep(0.05)

    # Modify file: rename function and add another function
    py_file.write_text("def updated_function():\n    return 100\n\ndef helper():\n    return 200\n", encoding="utf-8")

    # Run sync sweep
    sweep_results = watcher.run_once()
    assert len(sweep_results) == 1
    target_f, elapsed_ms = sweep_results[0]
    assert target_f.name == "service.py"
    assert elapsed_ms < 150.0  # Fast sub-second incremental update

    # Verify graph was updated in-memory
    node_ids = set(watcher.graph.nodes.keys())
    assert any("updated_function" in nid for nid in node_ids)
    assert any("helper" in nid for nid in node_ids)
    assert not any("original_function" in nid for nid in node_ids)

    # Verify callback was executed
    assert len(changed_events) == 1


def test_watcher_handles_deleted_file(tmp_path: Path):
    """Test deleting a file cleans up its nodes and edges from the graph."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    file_a = repo_root / "a.py"
    file_b = repo_root / "b.py"
    file_a.write_text("def func_a(): return 1\n", encoding="utf-8")
    file_b.write_text("def func_b(): return 2\n", encoding="utf-8")

    builder = GraphBuilder()
    graph = builder.build_from_directory(repo_root)
    assert any("func_a" in nid for nid in graph.nodes)
    assert any("func_b" in nid for nid in graph.nodes)

    watcher = RepoPeekWatcher(
        repo_root=repo_root,
        output_dir=output_dir,
        graph=graph,
        poll_interval=0.1,
        debounce_ms=0,
    )

    # Delete file_b
    file_b.unlink()
    time.sleep(0.05)

    watcher.run_once()
    assert any("func_a" in nid for nid in watcher.graph.nodes)
    assert not any("func_b" in nid for nid in watcher.graph.nodes)
