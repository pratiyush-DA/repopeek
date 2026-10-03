"""Multi-lens projections derived from the canonical repository property graph."""

from typing import Dict, Optional, Set

from repopeek.models.schema import CanonicalGraph, Edge, EdgeType


def project_lens(
    graph: CanonicalGraph,
    allowed_kinds: Optional[Set[str]] = None,
    allowed_edge_types: Optional[Set[EdgeType]] = None,
) -> CanonicalGraph:
    """Project a filtered sub-graph containing only specified node kinds and edge types."""
    sub_graph = CanonicalGraph(
        schema_version=graph.schema_version,
        repo_commit=graph.repo_commit,
        dirty=graph.dirty,
        tool_version=graph.tool_version,
    )

    # Filter nodes
    for nid, node in graph.nodes.items():
        if allowed_kinds is None or node.kind in allowed_kinds:
            sub_graph.add_node(node)

    sub_node_ids = set(sub_graph.nodes.keys())

    # Filter edges (both endpoints must exist in projected node set)
    for edge in graph.edges:
        if allowed_edge_types is not None and edge.type not in allowed_edge_types:
            continue
        if edge.src in sub_node_ids and edge.dst in sub_node_ids:
            sub_graph.add_edge(edge)

    return sub_graph


def get_module_lens(graph: CanonicalGraph) -> CanonicalGraph:
    """Module & File Lens: File-to-file structural dependencies and script executions."""
    sub_graph = CanonicalGraph(
        schema_version=graph.schema_version,
        repo_commit=graph.repo_commit,
        dirty=graph.dirty,
        tool_version=graph.tool_version,
    )

    for nid, node in graph.nodes.items():
        if node.kind in ("file", "module"):
            sub_graph.add_node(node)

    file_node_ids = set(sub_graph.nodes.keys())

    # Map each symbol node to its enclosing file node
    symbol_to_file: Dict[str, str] = {}
    for nid, node in graph.nodes.items():
        if node.span and node.span.file:
            for fnid, fnode in sub_graph.nodes.items():
                if fnode.span and fnode.span.file == node.span.file:
                    symbol_to_file[nid] = fnid
                    break

    # Add file-to-file dependency edges
    seen_edges: Set[tuple] = set()
    for edge in graph.edges:
        if edge.type in (EdgeType.IMPORTS, EdgeType.RUNS_SCRIPT, EdgeType.CALLS):
            src_file = edge.src if edge.src in file_node_ids else symbol_to_file.get(edge.src)
            dst_file = edge.dst if edge.dst in file_node_ids else symbol_to_file.get(edge.dst)
            if src_file and dst_file and src_file != dst_file:
                pair = (src_file, dst_file, edge.type)
                if pair not in seen_edges:
                    seen_edges.add(pair)
                    sub_graph.add_edge(
                        Edge(
                            src=src_file,
                            dst=dst_file,
                            type=edge.type,
                            confidence=edge.confidence,
                            evidence=edge.evidence,
                        )
                    )
    return sub_graph


def get_symbol_lens(graph: CanonicalGraph) -> CanonicalGraph:
    """Symbol & Containment Lens: File, class, and function nesting hierarchy."""
    return project_lens(
        graph=graph,
        allowed_kinds={"file", "module", "class", "function", "method"},
        allowed_edge_types={EdgeType.DEFINED_IN},
    )


def get_call_lens(graph: CanonicalGraph) -> CanonicalGraph:
    """Call Graph Lens: Direct function, method, and constructor invocation paths."""
    return project_lens(
        graph=graph,
        allowed_kinds={"function", "method", "command", "class"},
        allowed_edge_types={EdgeType.CALLS},
    )


def get_class_lens(graph: CanonicalGraph) -> CanonicalGraph:
    """Class Hierarchy Lens: OOP classes, inheritance relationships, and methods."""
    return project_lens(
        graph=graph,
        allowed_kinds={"class", "method"},
        allowed_edge_types={EdgeType.INHERITS, EdgeType.DEFINED_IN},
    )
