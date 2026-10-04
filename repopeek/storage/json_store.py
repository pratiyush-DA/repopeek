"""Deterministic canonical JSON serializer and sharded graph persistence engine."""

import json
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
import uuid

from repopeek.discovery.hasher import hash_content
from repopeek.graph.lenses import (
    get_bridges_lens,
    get_call_lens,
    get_class_lens,
    get_config_lens,
    get_data_entity_lens,
    get_data_lens,
    get_module_lens,
    get_process_lens,
    get_symbol_lens,
)
from repopeek.models.schema import CanonicalGraph, Edge, NodeCard


def serialize_graph_to_dict(graph: CanonicalGraph) -> Dict[str, Any]:
    """Serialize CanonicalGraph into a deterministic dictionary with stable sorting."""
    # Nodes sorted by ID
    sorted_node_cards = sorted(graph.nodes.values(), key=lambda n: n.id)
    nodes_data = [node.model_dump(exclude_none=True) for node in sorted_node_cards]

    # Edges sorted by (src, dst, type, confidence)
    sorted_edges = sorted(
        graph.edges,
        key=lambda e: (e.src, e.dst, e.type.value, e.confidence.value),
    )
    edges_data = [edge.model_dump(exclude_none=True) for edge in sorted_edges]

    return {
        "schema_version": graph.schema_version,
        "tool_version": graph.tool_version,
        "repo_commit": graph.repo_commit,
        "dirty": graph.dirty,
        "nodes": nodes_data,
        "edges": edges_data,
    }


def deserialize_graph_from_dict(data: Dict[str, Any]) -> CanonicalGraph:
    """Reconstruct CanonicalGraph from serialized dictionary representation."""
    graph = CanonicalGraph(
        schema_version=data.get("schema_version", "1.0.0"),
        tool_version=data.get("tool_version", "0.1.0"),
        repo_commit=data.get("repo_commit"),
        dirty=data.get("dirty", False),
    )

    nodes_raw = data.get("nodes", [])
    if isinstance(nodes_raw, list):
        for nd in nodes_raw:
            graph.add_node(NodeCard.model_validate(nd))
    elif isinstance(nodes_raw, dict):
        for nd in nodes_raw.values():
            graph.add_node(NodeCard.model_validate(nd))

    for ed in data.get("edges", []):
        graph.add_edge(Edge.model_validate(ed))

    return graph


def dump_deterministic_json(data: Any, target_path: Path) -> str:
    """Write deterministic formatted JSON with sorted keys, returning its SHA-256 hash."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    target_path.write_text(serialized, encoding="utf-8")
    return hash_content(serialized)


def save_canonical_graph(
    graph: CanonicalGraph,
    output_dir: Path,
    repo_root: Optional[Path] = None,
    materialize_lenses: bool = True,
) -> Dict[str, Any]:
    """Persist CanonicalGraph as sharded deterministic JSON artifacts with atomic swap."""
    out_dir = Path(output_dir).resolve()
    staging_dir = out_dir.parent / f".tmp_build_{uuid.uuid4().hex[:12]}"
    staging_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Full Graph
        graph_dict = serialize_graph_to_dict(graph)
        graph_file = staging_dir / "graph.json"
        graph_sha = dump_deterministic_json(graph_dict, graph_file)

        # 2. Materialized Lenses
        lenses_manifest: Dict[str, Any] = {}
        if materialize_lenses:
            lenses_dir = staging_dir / "lenses"
            lens_map = {
                "module": get_module_lens(graph),
                "symbol": get_symbol_lens(graph),
                "call": get_call_lens(graph),
                "class": get_class_lens(graph),
                "data": get_data_lens(graph),
                "data_entity": get_data_entity_lens(graph),
                "config": get_config_lens(graph),
                "process": get_process_lens(graph),
                "bridges": get_bridges_lens(graph),
            }

            for lname, lgraph in lens_map.items():
                ldict = serialize_graph_to_dict(lgraph)
                lfile = lenses_dir / f"{lname}.json"
                lsha = dump_deterministic_json(ldict, lfile)
                lenses_manifest[lname] = {
                    "file": f"lenses/{lname}.json",
                    "nodes_count": len(lgraph.nodes),
                    "edges_count": len(lgraph.edges),
                    "sha256": lsha,
                }

        # 3. Shards by source file
        shards_dir = staging_dir / "shards"
        files_map: Dict[str, List[str]] = {}
        for nid, node in graph.nodes.items():
            fpath = node.span.file if node.span and node.span.file else "_global"
            files_map.setdefault(fpath, []).append(nid)

        shards_manifest: Dict[str, Any] = {}
        for fpath, nids in files_map.items():
            shard_nodes = {nid: graph.nodes[nid] for nid in nids}
            nid_set = set(nids)
            shard_edges = [
                e for e in graph.edges
                if e.src in nid_set or e.dst in nid_set
            ]
            shard_graph = CanonicalGraph(
                schema_version=graph.schema_version,
                tool_version=graph.tool_version,
                repo_commit=graph.repo_commit,
                dirty=graph.dirty,
                nodes=shard_nodes,
                edges=shard_edges,
            )
            shard_dict = serialize_graph_to_dict(shard_graph)
            safe_rel_name = fpath.replace("/", "__").replace("\\", "__")
            shard_file = shards_dir / f"{safe_rel_name}.json"
            shard_sha = dump_deterministic_json(shard_dict, shard_file)
            shards_manifest[fpath] = {
                "file": f"shards/{safe_rel_name}.json",
                "nodes_count": len(shard_nodes),
                "edges_count": len(shard_edges),
                "sha256": shard_sha,
            }

        # 4. Manifest
        manifest = {
            "schema_version": graph.schema_version,
            "tool_version": graph.tool_version,
            "repo_commit": graph.repo_commit,
            "dirty": graph.dirty,
            "nodes_count": len(graph.nodes),
            "edges_count": len(graph.edges),
            "graph_sha256": graph_sha,
            "lenses": lenses_manifest,
            "shards": shards_manifest,
        }
        manifest_file = staging_dir / "manifest.json"
        dump_deterministic_json(manifest, manifest_file)

        # 5. Atomic directory swap
        if out_dir.exists():
            backup_dir = out_dir.parent / f".tmp_old_{uuid.uuid4().hex[:12]}"
            out_dir.rename(backup_dir)
            staging_dir.rename(out_dir)
            shutil.rmtree(backup_dir, ignore_errors=True)
        else:
            staging_dir.rename(out_dir)

        return manifest

    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise


def load_canonical_graph(storage_dir: Path) -> CanonicalGraph:
    """Load complete CanonicalGraph from persistent storage directory."""
    graph_path = Path(storage_dir) / "graph.json"
    if not graph_path.exists():
        raise FileNotFoundError(f"Canonical graph not found at {graph_path}")
    raw_text = graph_path.read_text(encoding="utf-8")
    data = json.loads(raw_text)
    return deserialize_graph_from_dict(data)


def load_lens(storage_dir: Path, lens_name: str) -> CanonicalGraph:
    """Load a specific materialised lens sub-graph from storage."""
    lens_path = Path(storage_dir) / "lenses" / f"{lens_name}.json"
    if not lens_path.exists():
        raise FileNotFoundError(f"Lens '{lens_name}' not found at {lens_path}")
    raw_text = lens_path.read_text(encoding="utf-8")
    data = json.loads(raw_text)
    return deserialize_graph_from_dict(data)


def load_manifest(storage_dir: Path) -> Dict[str, Any]:
    """Load storage manifest file."""
    manifest_path = Path(storage_dir) / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def load_file_shard(storage_dir: Path, rel_path: str) -> CanonicalGraph:
    """Load a sharded subgraph for a single repository source file."""
    safe_rel_name = rel_path.replace("/", "__").replace("\\", "__")
    shard_path = Path(storage_dir) / "shards" / f"{safe_rel_name}.json"
    if not shard_path.exists():
        raise FileNotFoundError(f"Shard for '{rel_path}' not found at {shard_path}")
    raw_text = shard_path.read_text(encoding="utf-8")
    data = json.loads(raw_text)
    return deserialize_graph_from_dict(data)


def update_file_shard(
    storage_dir: Path,
    rel_path: str,
    graph: CanonicalGraph,
) -> Path:
    """Save updated shard for a single source file in <10ms."""
    shards_dir = Path(storage_dir) / "shards"
    shards_dir.mkdir(parents=True, exist_ok=True)
    safe_rel_name = rel_path.replace("/", "__").replace("\\", "__")
    shard_file = shards_dir / f"{safe_rel_name}.json"

    shard_nodes = {
        nid: node for nid, node in graph.nodes.items()
        if node.span and node.span.file == rel_path
    }
    nid_set = set(shard_nodes.keys())
    shard_edges = [
        e for e in graph.edges
        if e.src in nid_set or e.dst in nid_set
    ]
    shard_graph = CanonicalGraph(
        schema_version=graph.schema_version,
        tool_version=graph.tool_version,
        repo_commit=graph.repo_commit,
        dirty=True,
        nodes=shard_nodes,
        edges=shard_edges,
    )
    shard_dict = serialize_graph_to_dict(shard_graph)
    shard_sha = dump_deterministic_json(shard_dict, shard_file)

    # Sync graph.json if present in storage_dir
    graph_file = Path(storage_dir) / "graph.json"
    if graph_file.exists():
        dump_deterministic_json(serialize_graph_to_dict(graph), graph_file)

    # Sync manifest.json if present
    manifest_file = Path(storage_dir) / "manifest.json"
    if manifest_file.exists():
        try:
            m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            m_data["nodes_count"] = len(graph.nodes)
            m_data["edges_count"] = len(graph.edges)
            m_data["dirty"] = True
            if "shards" in m_data:
                m_data["shards"][rel_path] = {
                    "file": f"shards/{safe_rel_name}.json",
                    "nodes_count": len(shard_nodes),
                    "edges_count": len(shard_edges),
                    "sha256": shard_sha,
                }
            dump_deterministic_json(m_data, manifest_file)
        except Exception:
            pass

    return shard_file

