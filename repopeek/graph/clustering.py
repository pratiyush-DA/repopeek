"""Community detection and clustering engine for RepoPeek canonical property graphs.

Uses Leiden (graspologic_native/graspologic) if available, falling back to
NetworkX Louvain with deterministic seeding and canonical ordering.
Computes community cohesion scores and semantic community labels.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from repopeek.models.schema import CanonicalGraph, NodeCard

_MIN_SPLIT_SIZE = 10
_MAX_COMMUNITY_FRACTION = 0.20


def _build_undirected_graph(graph: CanonicalGraph, exclude_config_nodes: bool = True) -> nx.Graph:
    """Build a deterministic undirected NetworkX graph from CanonicalGraph."""
    G = nx.Graph()
    # Add nodes sorted
    for nid in sorted(graph.nodes.keys()):
        node = graph.nodes[nid]
        if exclude_config_nodes and (node.kind in ("yaml_config", "json_config") or nid.startswith("ext:")):
            continue
        G.add_node(
            nid,
            kind=node.kind,
            sig=node.sig,
            file=node.span.file if node.span else "",
        )

    # Add edges canonically
    for edge in graph.edges:
        if edge.src in G and edge.dst in G and edge.src != edge.dst:
            G.add_edge(edge.src, edge.dst, type=edge.type.value if hasattr(edge.type, "value") else str(edge.type))

    return G


def _partition_nx_louvain(G: nx.Graph, resolution: float = 1.0) -> Dict[str, int]:
    """Run Louvain community detection using NetworkX."""
    try:
        import networkx.algorithms.community as nx_comm
        comms = nx_comm.louvain_communities(G, weight=None, resolution=resolution, seed=42)
        partition: Dict[str, int] = {}
        for cid, node_set in enumerate(comms):
            for n in node_set:
                partition[n] = cid
        return partition
    except Exception:
        # Fallback to greedy modularity
        try:
            import networkx.algorithms.community as nx_comm
            comms = nx_comm.greedy_modularity_communities(G, resolution=resolution)
            partition = {}
            for cid, node_set in enumerate(comms):
                for n in node_set:
                    partition[n] = cid
            return partition
        except Exception:
            return {n: 0 for n in G.nodes()}


def _partition(G: nx.Graph, resolution: float = 1.0) -> Dict[str, int]:
    """Try Leiden if graspologic is available, falling back to Louvain."""
    # Attempt native or standard Leiden
    try:
        import graspologic_native as gn
        edges = [(str(u), str(v), 1.0) for u, v in G.edges()]
        _quality, native_partitions = gn.leiden(
            edges=edges,
            starting_communities=None,
            resolution=resolution,
            randomness=0.001,
            iterations=1,
            use_modularity=True,
            seed=42,
            trials=1,
        )
        return {node_id: int(cid) for node_id, cid in native_partitions.items()}
    except Exception:
        pass

    try:
        from graspologic.partition import leiden
        return leiden(G, resolution=resolution, random_seed=42)
    except Exception:
        pass

    return _partition_nx_louvain(G, resolution=resolution)


def detect_communities(
    graph: CanonicalGraph,
    resolution: float = 1.0,
) -> Dict[int, List[str]]:
    """Partition graph nodes into modular communities.

    Returns dict mapping community_id -> sorted list of node IDs.
    """
    G = _build_undirected_graph(graph)

    if G.number_of_nodes() == 0:
        return {}

    isolates = [n for n in G.nodes() if G.degree(n) == 0]
    connected_nodes = [n for n in G.nodes() if G.degree(n) > 0]

    raw: Dict[int, List[str]] = {}
    if connected_nodes:
        subG = G.subgraph(connected_nodes)
        partition = _partition(subG, resolution=resolution)
        for node, cid in partition.items():
            raw.setdefault(cid, []).append(node)

    # Isolates become single-node communities
    next_cid = max(raw.keys(), default=-1) + 1
    for iso in isolates:
        raw[next_cid] = [iso]
        next_cid += 1

    # Split oversized communities if they dominate the graph
    max_size = max(_MIN_SPLIT_SIZE, int(G.number_of_nodes() * _MAX_COMMUNITY_FRACTION))
    final_communities: List[List[str]] = []
    for nodes in raw.values():
        if len(nodes) > max_size and len(nodes) > _MIN_SPLIT_SIZE:
            subG = G.subgraph(nodes)
            try:
                sub_part = _partition(subG, resolution=resolution * 1.5)
                sub_groups: Dict[int, List[str]] = {}
                for n, scid in sub_part.items():
                    sub_groups.setdefault(scid, []).append(n)
                if len(sub_groups) > 1:
                    final_communities.extend(list(sub_groups.values()))
                else:
                    final_communities.append(nodes)
            except Exception:
                final_communities.append(nodes)
        else:
            final_communities.append(nodes)

    # Sort communities deterministically: size descending, then lexical order
    final_communities.sort(key=lambda nodes: (-len(nodes), tuple(sorted(map(str, nodes)))))
    return {cid: sorted(nodes) for cid, nodes in enumerate(final_communities)}


def cohesion_score(G: nx.Graph, community_nodes: List[str]) -> float:
    """Compute density of internal connections within community (0.0 to 1.0)."""
    n = len(community_nodes)
    if n <= 1:
        return 1.0
    subG = G.subgraph(community_nodes)
    actual = subG.number_of_edges() - nx.number_of_selfloops(subG)
    possible = n * (n - 1) / 2
    return actual / possible if possible > 0 else 0.0


def compute_cohesion_scores(
    graph: CanonicalGraph,
    communities: Dict[int, List[str]],
) -> Dict[int, float]:
    """Compute cohesion scores for all detected communities."""
    G = _build_undirected_graph(graph)
    return {cid: cohesion_score(G, nodes) for cid, nodes in communities.items()}


def generate_community_labels(
    graph: CanonicalGraph,
    communities: Dict[int, List[str]],
) -> Dict[int, str]:
    """Generate meaningful human/agent labels for each community based on paths and hub symbols."""
    labels: Dict[int, str] = {}

    for cid, nodes in communities.items():
        if not nodes:
            labels[cid] = f"Community {cid}"
            continue

        dir_counter: Counter[str] = Counter()
        kind_counter: Counter[str] = Counter()
        names: List[str] = []

        for nid in nodes:
            card = graph.get_node(nid)
            if not card:
                continue
            if card.span and card.span.file:
                parent_dir = Path(card.span.file).parent.as_posix()
                if parent_dir and parent_dir != ".":
                    dir_counter[parent_dir] += 1
                else:
                    stem = Path(card.span.file).stem
                    dir_counter[stem] += 1
            kind_counter[card.kind] += 1
            if card.sig and len(card.sig) < 30:
                clean_sig = card.sig.split("(")[0].strip()
                if clean_sig and not clean_sig.startswith("__"):
                    names.append(clean_sig)

        # Most frequent directory or module
        top_dir = dir_counter.most_common(1)[0][0] if dir_counter else ""
        top_name = names[0] if names else ""

        if top_dir and top_name:
            label = f"{top_dir} ({top_name})"
        elif top_dir:
            label = top_dir
        elif top_name:
            label = top_name
        else:
            dominant_kind = kind_counter.most_common(1)[0][0] if kind_counter else "component"
            label = f"{dominant_kind} cluster {cid}"

        # Sanitize label
        label = label.replace("\\", "/").strip("/ ")
        labels[cid] = label or f"Community {cid}"

    return labels
