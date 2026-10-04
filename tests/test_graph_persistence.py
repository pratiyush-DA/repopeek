"""Tests for deterministic graph persistence, Git provenance, and SQLite cache."""

import json
from pathlib import Path
import pytest

from repopeek.graph.builder import GraphBuilder
from repopeek.models.schema import (
    CanonicalGraph,
    Confidence,
    Edge,
    EdgeType,
    Evidence,
    NodeCard,
    NodeFacts,
    NodeProvenance,
    NodeStory,
    Span,
)
from repopeek.storage.provenance import (
    GitProvenance,
    compute_repo_blob_shas,
    get_git_provenance,
)
from repopeek.storage.json_store import (
    deserialize_graph_from_dict,
    dump_deterministic_json,
    load_canonical_graph,
    load_file_shard,
    load_lens,
    load_manifest,
    save_canonical_graph,
    serialize_graph_to_dict,
    update_file_shard,
)
from repopeek.storage.sqlite_cache import (
    build_sqlite_cache,
    query_sqlite_edges,
    query_sqlite_impact,
    query_sqlite_nodes,
    update_sqlite_file,
)


def _make_sample_graph() -> CanonicalGraph:
    """Helper creating a minimal deterministic CanonicalGraph."""
    graph = CanonicalGraph(
        schema_version="1.0.0",
        tool_version="0.1.0",
        repo_commit="abc1234567890",
        dirty=False,
    )
    n1 = NodeCard(
        id="python:app/calc.py::add",
        kind="function",
        sig="def add(a: int, b: int) -> int",
        span=Span(file="app/calc.py", start=1, end=5),
        facts=NodeFacts(calls=0, params=["a", "b"], returns="int"),
        story=NodeStory(text="Adds two integers"),
        content_hash="hash_n1",
        provenance=NodeProvenance(commit="abc1234567890", blob_sha="blob_n1"),
    )
    n2 = NodeCard(
        id="python:app/calc.py::compute",
        kind="function",
        sig="def compute(x: int) -> int",
        span=Span(file="app/calc.py", start=7, end=12),
        facts=NodeFacts(calls=1, params=["x"], returns="int"),
        story=NodeStory(text="Computes total via add"),
        content_hash="hash_n2",
        provenance=NodeProvenance(commit="abc1234567890", blob_sha="blob_n1"),
    )
    n3 = NodeCard(
        id="python:app/main.py::run",
        kind="function",
        sig="def run() -> None",
        span=Span(file="app/main.py", start=1, end=10),
        facts=NodeFacts(calls=1),
        story=NodeStory(text="Application entry point"),
        content_hash="hash_n3",
        provenance=NodeProvenance(commit="abc1234567890", blob_sha="blob_n2"),
    )
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)

    # Edge: compute calls add
    graph.add_edge(
        Edge(
            src="python:app/calc.py::compute",
            dst="python:app/calc.py::add",
            type=EdgeType.CALLS,
            confidence=Confidence.RESOLVED,
            evidence=Evidence(
                file="app/calc.py",
                start_line=8,
                end_line=8,
                how_derived="ast_call",
            ),
        )
    )
    # Edge: run calls compute
    graph.add_edge(
        Edge(
            src="python:app/main.py::run",
            dst="python:app/calc.py::compute",
            type=EdgeType.CALLS,
            confidence=Confidence.RESOLVED,
            evidence=Evidence(
                file="app/main.py",
                start_line=5,
                end_line=5,
                how_derived="ast_call",
            ),
        )
    )
    return graph


def test_git_provenance_current_repo():
    """Verify git provenance extraction in current workspace."""
    repo_root = Path(__file__).parent.parent
    prov = get_git_provenance(repo_root)
    assert prov.is_git is True
    assert prov.commit is not None
    assert len(prov.commit) >= 7
    assert isinstance(prov.dirty, bool)


def test_git_provenance_non_git_dir(tmp_path: Path):
    """Verify non-git directory returns graceful fallback."""
    prov = get_git_provenance(tmp_path)
    assert prov.is_git is False
    assert prov.commit is None
    assert prov.dirty is False


def test_compute_repo_blob_shas(tmp_path: Path):
    """Verify blob SHA computation matches git format."""
    f1 = tmp_path / "hello.py"
    f1.write_text("print('hello')", encoding="utf-8")
    shas = compute_repo_blob_shas(tmp_path, [f1])
    assert "hello.py" in shas
    assert len(shas["hello.py"]) == 40


def test_deterministic_serialization_roundtrip(tmp_path: Path):
    """Verify deterministic JSON serialization is byte-identical across calls and roundtrips."""
    graph = _make_sample_graph()
    dict1 = serialize_graph_to_dict(graph)
    dict2 = serialize_graph_to_dict(graph)
    assert dict1 == dict2

    target1 = tmp_path / "graph1.json"
    target2 = tmp_path / "graph2.json"
    sha1 = dump_deterministic_json(dict1, target1)
    sha2 = dump_deterministic_json(dict2, target2)

    assert sha1 == sha2
    assert target1.read_text(encoding="utf-8") == target2.read_text(encoding="utf-8")

    # Roundtrip verification
    reloaded = deserialize_graph_from_dict(dict1)
    assert len(reloaded.nodes) == len(graph.nodes)
    assert len(reloaded.edges) == len(graph.edges)
    assert reloaded.repo_commit == graph.repo_commit
    assert "python:app/calc.py::add" in reloaded.nodes
    assert reloaded.nodes["python:app/calc.py::add"].sig == "def add(a: int, b: int) -> int"


def test_save_and_load_canonical_graph(tmp_path: Path):
    """Verify sharded JSON persistence, manifest creation, and loaders."""
    graph = _make_sample_graph()
    storage_dir = tmp_path / ".repopeek"

    manifest = save_canonical_graph(graph, storage_dir, materialize_lenses=True)
    assert (storage_dir / "graph.json").exists()
    assert (storage_dir / "manifest.json").exists()
    assert (storage_dir / "lenses").is_dir()
    assert (storage_dir / "shards").is_dir()

    assert manifest["nodes_count"] == 3
    assert manifest["edges_count"] == 2
    assert "call" in manifest["lenses"]
    assert len(manifest["shards"]) == 2

    # Load canonical graph
    loaded_graph = load_canonical_graph(storage_dir)
    assert len(loaded_graph.nodes) == 3
    assert len(loaded_graph.edges) == 2

    # Load manifest
    loaded_manifest = load_manifest(storage_dir)
    assert loaded_manifest["nodes_count"] == 3

    # Load lens
    call_lens = load_lens(storage_dir, "call")
    assert len(call_lens.edges) == 2

    # Load shard
    calc_shard = load_file_shard(storage_dir, "app/calc.py")
    assert len(calc_shard.nodes) == 2
    assert "python:app/calc.py::add" in calc_shard.nodes

    # Atomic re-save over existing directory
    manifest2 = save_canonical_graph(graph, storage_dir, materialize_lenses=True)
    assert manifest2["graph_sha256"] == manifest["graph_sha256"]


def test_sqlite_cache_and_recursive_impact(tmp_path: Path):
    """Verify SQLite cache creation, indexing, and recursive CTE impact query."""
    graph = _make_sample_graph()
    db_path = tmp_path / "cache.db"

    build_sqlite_cache(graph, db_path)
    assert db_path.exists()

    # Query nodes
    func_nodes = query_sqlite_nodes(db_path, kind="function")
    assert len(func_nodes) == 3

    file_nodes = query_sqlite_nodes(db_path, file="app/calc.py")
    assert len(file_nodes) == 2

    # Query edges
    call_edges = query_sqlite_edges(db_path, edge_type="CALLS")
    assert len(call_edges) == 2

    # Recursive upstream impact of modifying 'python:app/calc.py::add'
    # compute calls add (depth 1), run calls compute (depth 2)
    impact = query_sqlite_impact(db_path, target_id="python:app/calc.py::add", max_depth=5)
    assert len(impact) == 2
    assert impact[0]["src"] == "python:app/calc.py::compute"
    assert impact[0]["depth"] == 1
    assert impact[1]["src"] == "python:app/main.py::run"
    assert impact[1]["depth"] == 2


def test_end_to_end_persistence_sample_repo(tmp_path: Path):
    """Verify end-to-end building, provenance injection, and persistence on sample repo."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_repo"
    builder = GraphBuilder()
    graph = builder.build_from_directory(fixture_path)

    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0

    # Ensure nodes have provenance with blob_sha
    for node in graph.nodes.values():
        if node.span and node.span.file:
            assert node.provenance is not None
            assert node.provenance.blob_sha is not None

    storage_dir = tmp_path / ".repopeek"
    manifest = save_canonical_graph(graph, storage_dir)
    assert manifest["nodes_count"] == len(graph.nodes)

    # SQLite cache impact query on invoices table or parse_invoice
    db_path = storage_dir / "cache.db"
    build_sqlite_cache(graph, db_path)
    assert db_path.exists()

    impact = query_sqlite_impact(db_path, target_id="sql:db/queries.sql::table.invoices", max_depth=5)
    assert len(impact) > 0
    # The source should include the invoice parser or embedded query
    sources = {r["src"] for r in impact}
    assert any("invoice.py" in s for s in sources)


def test_incremental_update_file(tmp_path: Path):
    """Verify incremental single-file update keeps graph, shards, and SQLite cache in sync."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_repo"
    builder = GraphBuilder()
    graph = builder.build_from_directory(fixture_path)

    storage_dir = tmp_path / ".repopeek"
    manifest = save_canonical_graph(graph, storage_dir)
    db_path = storage_dir / "cache.db"
    build_sqlite_cache(graph, db_path)

    invoice_file = fixture_path / "src" / "billing" / "invoice.py"
    rel_path = "src/billing/invoice.py"

    # Perform single-file update
    updated_graph = builder.update_file(invoice_file, graph, repo_root=fixture_path)
    assert len(updated_graph.nodes) > 0

    # Save shard and sync graph.json / manifest
    shard_file = update_file_shard(storage_dir, rel_path, updated_graph)
    assert shard_file.exists()

    # Update SQLite cache
    update_sqlite_file(rel_path, updated_graph, db_path)

    # Verify updated nodes in SQLite cache
    nodes = query_sqlite_nodes(db_path, file=rel_path)
    assert len(nodes) > 0
    assert any("InvoiceParser" in n["id"] for n in nodes)

