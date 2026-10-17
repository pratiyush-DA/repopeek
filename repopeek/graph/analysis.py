"""Graph topological analysis engine: god nodes, surprising connections, cycles, and architectural questions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from repopeek.models.schema import CanonicalGraph, Edge, EdgeType, NodeCard


# Builtin/mock and primitive noise labels to exclude from god nodes
_BUILTIN_NOISE_LABELS: frozenset[str] = frozenset({
    "str", "int", "float", "bool", "bytes", "bytearray", "complex", "object",
    "True", "False", "None",
    "MagicMock", "Mock", "AsyncMock", "NonCallableMock",
    "PropertyMock", "patch", "sentinel",
    # Python typing and stdlib
    "Path", "Any", "Optional", "List", "Dict", "Set", "Tuple", "Union",
    "Callable", "Type", "ClassVar", "Final", "Literal", "Protocol",
    "Counter", "defaultdict", "OrderedDict", "datetime", "Enum",
    "os", "sys", "re", "json", "io", "abc", "typing",
    # Standard language primitives and builtins
    "String", "Int", "Double", "Float", "Bool", "Data", "URL", "Date", "UUID",
    "void", "char", "long", "short", "unsigned", "signed",
    "error", "nil", "string", "int32", "int64", "uint32", "uint64", "byte", "rune",
    "len", "range", "print", "isinstance", "issubclass", "enumerate", "zip", "sum",
    "max", "min", "getattr", "setattr", "hasattr", "delattr", "open", "type", "list",
    "dict", "set", "tuple", "iter", "next", "repr", "super", "any", "all", "abs",
    "round", "sorted", "filter", "map", "format", "callable", "id",
})

_JSON_NOISE_LABELS: frozenset[str] = frozenset({
    "start", "end", "name", "id", "type", "properties",
    "value", "key", "data", "items", "title", "description", "version",
    "dependencies", "devdependencies", "peerdependencies",
    "optionaldependencies", "bundleddependencies",
})


def _is_file_node(card: NodeCard) -> bool:
    """Return True if this node represents a whole file container rather than an abstraction."""
    if card.kind in ("file", "repository"):
        return True
    return False


def _is_noise_node(card: NodeCard) -> bool:
    """Return True if node is standard library noise, external, unresolved, or config node."""
    # Exclude external and unresolved symbols
    if card.id.startswith("ext:") or card.kind in ("external", "external_symbol", "unresolved"):
        return True

    # Exclude nodes without a real source file location
    if not card.span or not card.span.file:
        return True

    # Exclude configuration entries
    if card.kind in ("json_config", "yaml_config", "config"):
        return True

    sig = (card.sig or "").strip()
    if sig in _BUILTIN_NOISE_LABELS:
        return True
    ident = card.id.split("::")[-1] if "::" in card.id else card.id
    if ident in _BUILTIN_NOISE_LABELS:
        return True
    if ident.lower() in _JSON_NOISE_LABELS:
        return True
    return False


def _get_node_label(card: Optional[NodeCard], node_id: str) -> str:
    if card and card.sig:
        return card.sig
    if card and card.id:
        return card.id.split("::")[-1]
    return node_id.split("::")[-1] if "::" in node_id else node_id


def god_nodes(
    graph: CanonicalGraph,
    top_n: int = 10,
    exclude_hubs_percentile: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Identify the top_n most connected real code entities (core abstractions).

    File container nodes and language primitive noise are excluded.
    """
    in_degrees: Dict[str, int] = {}
    out_degrees: Dict[str, int] = {}

    for nid in graph.nodes:
        in_degrees[nid] = 0
        out_degrees[nid] = 0

    for edge in graph.edges:
        out_degrees[edge.src] = out_degrees.get(edge.src, 0) + 1
        in_degrees[edge.dst] = in_degrees.get(edge.dst, 0) + 1

    total_degrees = {
        nid: in_degrees.get(nid, 0) + out_degrees.get(nid, 0)
        for nid in graph.nodes
    }

    hub_threshold: Optional[float] = None
    if exclude_hubs_percentile is not None and total_degrees:
        sorted_degs = sorted(total_degrees.values())
        idx = max(0, int(len(sorted_degs) * exclude_hubs_percentile / 100) - 1)
        hub_threshold = sorted_degs[idx]

    candidates = sorted(total_degrees.items(), key=lambda x: x[1], reverse=True)
    results: List[Dict[str, Any]] = []

    for nid, deg in candidates:
        if hub_threshold is not None and deg > hub_threshold:
            continue
        card = graph.get_node(nid)
        if not card:
            continue
        if _is_file_node(card) or _is_noise_node(card):
            continue

        label = _get_node_label(card, nid)
        file_path = card.span.file if card.span else ""
        results.append({
            "id": nid,
            "label": label,
            "kind": card.kind,
            "degree": deg,
            "in_degree": in_degrees.get(nid, 0),
            "out_degree": out_degrees.get(nid, 0),
            "file": file_path,
            "start_line": card.span.start if card.span else 1,
            "complexity": card.facts.complexity if card.facts else 1,
        })
        if len(results) >= top_n:
            break

    return results


def surprising_connections(
    graph: CanonicalGraph,
    communities: Optional[Dict[int, List[str]]] = None,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """Detect non-obvious or unexpected connections across modules, communities, or languages."""
    node_to_comm: Dict[str, int] = {}
    if communities:
        for cid, member_ids in communities.items():
            for mid in member_ids:
                node_to_comm[mid] = cid

    scored_edges: List[Tuple[int, List[str], Edge]] = []

    for edge in graph.edges:
        src_card = graph.get_node(edge.src)
        dst_card = graph.get_node(edge.dst)
        if not src_card or not dst_card:
            continue
        # Skip file-to-symbol DEFINED_IN edges as they are purely structural
        if edge.type == EdgeType.DEFINED_IN:
            continue

        score = 0
        reasons: List[str] = []

        # 1. Confidence score bonus
        conf = edge.confidence.value if hasattr(edge.confidence, "value") else str(edge.confidence)
        if conf in ("ambiguous", "dynamic", "unresolved"):
            score += 3
            reasons.append(f"{conf} resolution - dynamic or ambiguous coupling")
        elif conf == "external":
            score += 1
            reasons.append("external boundary link")

        # 2. Cross-file bonus
        src_file = src_card.span.file if src_card.span else ""
        dst_file = dst_card.span.file if dst_card.span else ""
        if src_file and dst_file and src_file != dst_file:
            score += 1
            # Cross-directory
            src_dir = Path(src_file).parent.as_posix()
            dst_dir = Path(dst_file).parent.as_posix()
            if src_dir != dst_dir:
                score += 2
                reasons.append(f"crosses directory boundary ({src_dir} <-> {dst_dir})")

            # Cross-language
            src_ext = Path(src_file).suffix.lower()
            dst_ext = Path(dst_file).suffix.lower()
            if src_ext and dst_ext and src_ext != dst_ext:
                score += 3
                reasons.append(f"polyglot boundary bridge ({src_ext} <-> {dst_ext})")

        # 3. Cross-community bonus
        if node_to_comm:
            src_comm = node_to_comm.get(edge.src)
            dst_comm = node_to_comm.get(edge.dst)
            if src_comm is not None and dst_comm is not None and src_comm != dst_comm:
                score += 3
                reasons.append(f"bridges distinct community clusters (#{src_comm} <-> #{dst_comm})")

        if score > 0:
            scored_edges.append((score, reasons, edge))

    scored_edges.sort(key=lambda x: x[0], reverse=True)

    results: List[Dict[str, Any]] = []
    seen_pairs: Set[Tuple[str, str]] = set()

    for score, reasons, edge in scored_edges:
        pair = (edge.src, edge.dst)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        src_card = graph.get_node(edge.src)
        dst_card = graph.get_node(edge.dst)

        results.append({
            "src": edge.src,
            "dst": edge.dst,
            "src_label": _get_node_label(src_card, edge.src),
            "dst_label": _get_node_label(dst_card, edge.dst),
            "type": edge.type.value if hasattr(edge.type, "value") else str(edge.type),
            "score": score,
            "reasons": reasons,
            "confidence": edge.confidence.value if hasattr(edge.confidence, "value") else str(edge.confidence),
        })
        if len(results) >= top_n:
            break

    return results


def find_import_cycles(graph: CanonicalGraph) -> List[List[str]]:
    """Identify circular dependencies in the repository using Strongly Connected Components."""
    # Build file-level dependency directed graph
    file_graph = nx.DiGraph()

    # Non-code file extensions to exclude from import cycle analysis
    _non_code_exts = frozenset({".md", ".rst", ".txt", ".json", ".yaml", ".yml", ".toml", ".csv", ".tsv"})

    for edge in graph.edges:
        if edge.type != EdgeType.IMPORTS:
            continue

        src_card = graph.get_node(edge.src)
        dst_card = graph.get_node(edge.dst)
        src_file = src_card.span.file if src_card and src_card.span else None
        dst_file = dst_card.span.file if dst_card and dst_card.span else None

        if src_file and dst_file and src_file != dst_file:
            if Path(src_file).suffix.lower() in _non_code_exts or Path(dst_file).suffix.lower() in _non_code_exts:
                continue
            file_graph.add_edge(src_file, dst_file)

    cycles: List[List[str]] = []
    try:
        # Find all elementary cycles up to length limit to avoid explosion on dense graphs
        simple_cycles_gen = nx.simple_cycles(file_graph)
        count = 0
        for cycle in simple_cycles_gen:
            if len(cycle) >= 2:
                cycles.append(cycle + [cycle[0]])
                count += 1
                if count >= 20:
                    break
    except Exception:
        # Fallback to strongly connected components
        sccs = nx.strongly_connected_components(file_graph)
        for scc in sccs:
            if len(scc) > 1:
                cycles.append(list(scc))

    return cycles


def suggest_questions(
    graph: CanonicalGraph,
    communities: Optional[Dict[int, List[str]]] = None,
    top_n: int = 7,
) -> List[str]:
    """Generate high-value, actionable architectural questions for developers and AI agents."""
    questions: List[str] = []

    # 1. God nodes questions
    top_gods = god_nodes(graph, top_n=3)
    for g in top_gods:
        label = g["label"]
        deg = g["degree"]
        f = g["file"]
        file_part = f" in `{f}`" if f else ""
        questions.append(
            f"God node `{label}`{file_part} has {deg} connections. Does it violate Single Responsibility Principle, and can its public interface be decomposed?"
        )

    # 2. Cycle questions
    cycles = find_import_cycles(graph)
    if cycles:
        cycle = cycles[0]
        cycle_str = " -> ".join(Path(p).name for p in cycle[:4])
        questions.append(
            f"Circular dependency detected ({cycle_str}). Can an intermediate abstraction or event emitter break this cycle?"
        )

    # 3. Surprising connections questions
    surprises = surprising_connections(graph, communities=communities, top_n=3)
    for s in surprises:
        src = s["src_label"]
        dst = s["dst_label"]
        reasons = "; ".join(s["reasons"][:2])
        questions.append(
            f"Bridge `{src}` -> `{dst}` ({reasons}). Is this intentional cross-boundary coordination or unintended architectural leakage?"
        )

    # 4. Community cohesion question
    if communities and len(communities) > 1:
        questions.append(
            f"Graph was clustered into {len(communities)} modular communities. Are boundary interfaces between clusters strictly typed and versioned?"
        )

    return questions[:top_n]


def graph_diff(
    old_graph: CanonicalGraph,
    new_graph: CanonicalGraph,
) -> Dict[str, Any]:
    """Compute structural diff between two property graphs."""
    old_node_ids = set(old_graph.nodes.keys())
    new_node_ids = set(new_graph.nodes.keys())

    added_nodes = list(new_node_ids - old_node_ids)
    removed_nodes = list(old_node_ids - new_node_ids)

    modified_nodes: List[str] = []
    for nid in old_node_ids.intersection(new_node_ids):
        old_card = old_graph.nodes[nid]
        new_card = new_graph.nodes[nid]
        if old_card.content_hash != new_card.content_hash:
            modified_nodes.append(nid)

    def _edge_key(e: Edge) -> Tuple[str, str, str]:
        t = e.type.value if hasattr(e.type, "value") else str(e.type)
        return (e.src, e.dst, t)

    old_edge_set = {_edge_key(e) for e in old_graph.edges}
    new_edge_set = {_edge_key(e) for e in new_graph.edges}

    added_edges = [
        {"src": src, "dst": dst, "type": t}
        for (src, dst, t) in (new_edge_set - old_edge_set)
    ]
    removed_edges = [
        {"src": src, "dst": dst, "type": t}
        for (src, dst, t) in (old_edge_set - new_edge_set)
    ]

    return {
        "added_nodes_count": len(added_nodes),
        "removed_nodes_count": len(removed_nodes),
        "modified_nodes_count": len(modified_nodes),
        "added_edges_count": len(added_edges),
        "removed_edges_count": len(removed_edges),
        "added_nodes": added_nodes[:50],
        "removed_nodes": removed_nodes[:50],
        "modified_nodes": modified_nodes[:50],
        "added_edges": added_edges[:50],
        "removed_edges": removed_edges[:50],
    }
