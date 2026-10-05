"""Multi-lens projections derived from the canonical repository property graph."""

from typing import Any, Dict, List, Optional, Set

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


def get_data_lens(graph: CanonicalGraph) -> CanonicalGraph:
    """Data & Variable Def-Use Lens: Variable definitions, mutations, reads, and data state flow."""
    return project_lens(
        graph=graph,
        allowed_kinds={"variable", "function", "method", "class"},
        allowed_edge_types={EdgeType.READS, EdgeType.WRITES, EdgeType.DEFINED_IN},
    )


def get_data_entity_lens(graph: CanonicalGraph) -> CanonicalGraph:
    """Data-Entity Lens: Database tables, SQL queries, configuration entities, and code accesses."""
    return project_lens(
        graph=graph,
        allowed_kinds={"sql_table", "sql_query", "json_config", "yaml_config", "function", "method"},
        allowed_edge_types={EdgeType.READS, EdgeType.WRITES, EdgeType.EMBEDS_SQL},
    )


def get_config_lens(graph: CanonicalGraph) -> CanonicalGraph:
    """Config & Environment Lens: Configuration keys, env vars, and readers/writers."""
    sub_graph = CanonicalGraph(
        schema_version=graph.schema_version,
        repo_commit=graph.repo_commit,
        dirty=graph.dirty,
        tool_version=graph.tool_version,
    )

    config_kinds = {"json_config", "yaml_config", "file", "shell_script"}
    config_node_ids = {
        nid for nid, node in graph.nodes.items()
        if node.kind in config_kinds or nid.startswith("json:") or nid.startswith("yaml:")
    }

    relevant_edges: List[Edge] = []
    relevant_nodes: Set[str] = set()

    for edge in graph.edges:
        if edge.src in config_node_ids or edge.dst in config_node_ids:
            if edge.type in (EdgeType.READS, EdgeType.WRITES, EdgeType.DEFINED_IN):
                relevant_edges.append(edge)
                relevant_nodes.add(edge.src)
                relevant_nodes.add(edge.dst)

    for nid in relevant_nodes:
        node = graph.nodes.get(nid)
        if node:
            sub_graph.add_node(node)

    for edge in relevant_edges:
        if edge.src in sub_graph.nodes and edge.dst in sub_graph.nodes:
            sub_graph.add_edge(edge)

    return sub_graph


def get_process_lens(graph: CanonicalGraph) -> CanonicalGraph:
    """Process & Shell Script Lens: Shell scripts, commands, pipelines, and executed targets."""
    return project_lens(
        graph=graph,
        allowed_kinds={"file", "shell_script", "command"},
        allowed_edge_types={EdgeType.RUNS_SCRIPT, EdgeType.DEFINED_IN, EdgeType.READS, EdgeType.WRITES},
    )


def get_bridges_lens(graph: CanonicalGraph) -> CanonicalGraph:
    """Cross-Language Bridges Lens: Cross-boundary connections between Python, SQL, Shell, and Config."""
    sub_graph = CanonicalGraph(
        schema_version=graph.schema_version,
        repo_commit=graph.repo_commit,
        dirty=graph.dirty,
        tool_version=graph.tool_version,
    )

    bridge_edges: List[Edge] = []
    bridge_node_ids: Set[str] = set()

    for edge in graph.edges:
        is_bridge = False
        if edge.type in (EdgeType.EMBEDS_SQL, EdgeType.RUNS_SCRIPT):
            is_bridge = True
        elif edge.type in (EdgeType.READS, EdgeType.WRITES, EdgeType.INVOKES):
            src_lang = edge.src.split(":")[0] if ":" in edge.src else ""
            dst_lang = edge.dst.split(":")[0] if ":" in edge.dst else ""
            if src_lang and dst_lang and src_lang != dst_lang:
                is_bridge = True

        if is_bridge:
            bridge_edges.append(edge)
            bridge_node_ids.add(edge.src)
            bridge_node_ids.add(edge.dst)

    for nid in bridge_node_ids:
        node = graph.nodes.get(nid)
        if node:
            sub_graph.add_node(node)

    for edge in bridge_edges:
        if edge.src in sub_graph.nodes and edge.dst in sub_graph.nodes:
            sub_graph.add_edge(edge)

    return sub_graph


def trace_variable_flow(graph: CanonicalGraph, variable_name: str) -> Dict[str, Any]:
    """Trace where a variable is defined, written, and read across functions.

    Answers: 'Where is this variable written, where is it read, and what does it flow into?'
    """
    var_nodes = [
        n for nid, n in graph.nodes.items()
        if (nid == variable_name or nid.endswith(f"::{variable_name}") or nid.endswith(f".{variable_name}"))
        and n.kind == "variable"
    ]
    matched_id = var_nodes[0].id if var_nodes else variable_name

    writers: List[str] = []
    readers: List[str] = []
    defined_in: Optional[str] = None

    for edge in graph.edges:
        if edge.dst == matched_id:
            if edge.type == EdgeType.WRITES:
                writers.append(edge.src)
            elif edge.type == EdgeType.READS:
                readers.append(edge.src)
            elif edge.type == EdgeType.DEFINED_IN:
                defined_in = edge.src
        elif edge.src == matched_id and edge.type == EdgeType.DEFINED_IN:
            defined_in = edge.dst

    return {
        "variable": matched_id,
        "defined_in": defined_in,
        "writers": sorted(list(set(writers))),
        "readers": sorted(list(set(readers))),
    }


def trace_impact(graph: CanonicalGraph, target_id: str, max_depth: int = 5) -> Dict[str, Any]:
    """Compute the upstream blast radius / impact tree for a given node.

    Answers: 'If I change X, which functions, files, tables, and config keys can be affected?'
    Traverses reverse CALLS, READS, RUNS_SCRIPT, and IMPORTS up to max_depth.
    """
    affected_nodes: Set[str] = set()
    queue = [(target_id, 0)]
    visited = {target_id}

    incoming: Dict[str, List[Edge]] = {}
    for edge in graph.edges:
        incoming.setdefault(edge.dst, []).append(edge)

    while queue:
        curr, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        for in_edge in incoming.get(curr, []):
            src = in_edge.src
            if src not in visited:
                visited.add(src)
                affected_nodes.add(src)
                queue.append((src, depth + 1))

    categorized: Dict[str, List[str]] = {
        "functions": [],
        "files": [],
        "tables": [],
        "configs": [],
        "commands": [],
    }
    for nid in sorted(affected_nodes):
        card = graph.nodes.get(nid)
        if not card:
            continue
        if card.kind in ("function", "method"):
            categorized["functions"].append(nid)
        elif card.kind in ("file", "module"):
            categorized["files"].append(nid)
        elif card.kind == "sql_table":
            categorized["tables"].append(nid)
        elif card.kind in ("json_config", "yaml_config"):
            categorized["configs"].append(nid)
        elif card.kind in ("command", "shell_script"):
            categorized["commands"].append(nid)

    return {
        "target": target_id,
        "total_affected": len(affected_nodes),
        "affected_node_ids": sorted(list(affected_nodes)),
        "by_kind": categorized,
    }
