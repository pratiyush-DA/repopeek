"""Mathematical traversal confidence scoring and evidence-backed blast radius engine.

Implements the calibrated multi-hop confidence formulas and blast-radius partitioning
defined in the Phase 3 architecture specification:

1. Path Confidence:
   PathConfidence(P) = min(0.99, prod(c_i) * exp(-0.25 * (h - 1)))

2. Multi-Path Combination:
   CombinedConfidence(N) = min(0.99, 1 - prod(1 - PathConfidence(P_j)))

3. Graph Relevance (Distance Decay):
   GraphScore(N) = CombinedConfidence(N) * exp(-0.70 * (distance - 1))

4. Evidence-backed blast radius partitioning:
   - direct: Immediate 1-hop dependencies or combined confidence >= 0.80
   - indirect: Multi-hop dependencies with confidence >= threshold (default 0.20)
   - excluded: Pruned dependencies with confidence < threshold or exceeded depth
"""

from collections import deque
from dataclasses import asdict, dataclass, field
import fnmatch
import json
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# Hard ceiling on the serialized impact payload so a high-degree hub node cannot emit a
# multi-hundred-KB report. Budgeted on the compact (no-indent) dict; the MCP layer may
# pretty-print (~+15%), so this stays well below the neighbors < 15k bar.
MAX_IMPACT_PAYLOAD_CHARS = 11500

from repopeek.models.schema import CanonicalGraph, Confidence, Edge, EdgeType
from repopeek.graph.identity import is_config_kind, is_sql_table_kind, language_from_node_id


# Safety bounds so a query can never emit an effectively unbounded report.
MAX_EXPANSION_NODES = 200
MAX_FANOUT = 24
HIGH_DEGREE_THRESHOLD = 40
MAX_TRAVERSED_EDGES = 400
MAX_DIRECT_REPORT = 80
MAX_INDIRECT_REPORT = 40

_CROSS_LANG_EDGE_TYPES = {
    EdgeType.INVOKES,
    EdgeType.CO_CHANGED_WITH,
    EdgeType.EMBEDS_SQL,
    EdgeType.READS,
    EdgeType.WRITES,
}

_EDGE_EXPAND_PRIORITY = {
    "CALLS": 0,
    "INHERITS": 1,
    "IMPLEMENTS": 2,
    "INVOKES": 3,
    "DEFINED_IN": 4,
    "TESTS_CODE": 5,
    "WRITES": 6,
    "READS": 7,
    "EMBEDS_SQL": 8,
    "IMPORTS": 9,
    "RUNS_SCRIPT": 10,
    "CO_CHANGED_WITH": 11,
}
# Calibrated priors for relationship types and confidence enums
EDGE_CONFIDENCE_PRIORS: Dict[str, float] = {
    # Relational types
    "CALLS": 0.95,
    "INHERITS": 0.95,
    "IMPLEMENTS": 0.95,
    "DEFINED_IN": 0.95,
    "WRITES": 0.85,
    "READS": 0.85,
    "EMBEDS_SQL": 0.85,
    "IMPORTS": 0.80,
    "RUNS_SCRIPT": 0.80,
    "INVOKES": 0.75,
    "TESTS_CODE": 0.90,
    "CO_CHANGED_WITH": 0.70,
    # Confidence enum levels
    "resolved": 0.95,
    "ambiguous": 0.50,
    "dynamic": 0.50,
    "external": 0.40,
    "unresolved": 0.30,
}


def get_edge_prior(edge: Edge) -> float:
    """Compute the prior confidence score for a graph edge."""
    # 1. Base confidence from edge enum
    conf_enum = edge.confidence.value if hasattr(edge.confidence, "value") else str(edge.confidence)
    base_conf = EDGE_CONFIDENCE_PRIORS.get(conf_enum.lower(), 0.80)

    # 2. Relationship type prior
    type_str = edge.type.value if hasattr(edge.type, "value") else str(edge.type)
    type_prior = EDGE_CONFIDENCE_PRIORS.get(type_str, 0.80)

    # If edge confidence is explicitly resolved, respect the type prior
    if conf_enum.lower() == "resolved":
        return type_prior
    # Otherwise discount by uncertainty level
    return round(min(base_conf, type_prior), 4)


def calculate_path_confidence(step_confidences: List[float]) -> float:
    """Calculate multi-hop path confidence with exponential decay.

    Formula: PathConfidence(P) = min(0.99, prod(c_i) * exp(-0.25 * (h - 1)))
    """
    if not step_confidences:
        return 0.0

    h = len(step_confidences)
    prod_c = math.prod(step_confidences)
    decay = math.exp(-0.25 * (h - 1))
    return round(min(0.99, prod_c * decay), 6)


def calculate_combined_confidence(path_confidences: List[float]) -> float:
    """Combine multiple independent paths to a target node.

    Formula: CombinedConfidence(N) = min(0.99, 1 - prod(1 - P_j))
    """
    if not path_confidences:
        return 0.0

    prod_unseen = math.prod(max(0.0, 1.0 - p) for p in path_confidences)
    return round(min(0.99, 1.0 - prod_unseen), 6)


def calculate_graph_score(combined_confidence: float, distance: int) -> float:
    """Calculate distance-decayed graph relevance score.

    Formula: GraphScore(N) = CombinedConfidence(N) * exp(-0.70 * (distance - 1))
    """
    if distance < 1:
        distance = 1
    decay = math.exp(-0.70 * (distance - 1))
    return round(combined_confidence * decay, 6)


@dataclass
class BlastRadiusStep:
    """A single relational hop in a blast-radius path."""
    src: str
    dst: str
    type: str
    confidence: float
    flow: str  # "upstream" or "downstream"
    citation: Optional[str] = None
    how_derived: Optional[str] = None


@dataclass
class BlastRadiusPath:
    """A complete path from the origin target to an affected node."""
    hops: List[BlastRadiusStep]
    path_confidence: float


@dataclass
class AffectedNode:
    """An affected node within the blast radius with calibrated confidence and evidence."""
    node_id: str
    kind: str
    file: Optional[str]
    citation: Optional[str]
    distance: int
    combined_confidence: float
    graph_score: float
    category: str  # "direct" or "indirect"
    paths: List[BlastRadiusPath] = field(default_factory=list)
    story: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # Compact serialization. The full per-hop ``paths`` evidence is intentionally
        # omitted: on hub nodes it balloons the payload to hundreds of KB, and no consumer
        # (compiler, MCP, CLI, viewer) reads it from the dict — they use confidence,
        # citation, distance, and graph_score. Hop detail stays on the dataclass object.
        story = self.story
        if story and len(story) > 160:
            story = story[:160] + "…"
        return {
            "node_id": self.node_id,
            "kind": self.kind,
            "file": self.file,
            "citation": self.citation,
            "distance": self.distance,
            "combined_confidence": self.combined_confidence,
            "confidence": self.combined_confidence,
            "graph_score": self.graph_score,
            "category": self.category,
            "path_count": len(self.paths),
            "top_path_confidence": self.paths[0].path_confidence if self.paths else 0.0,
            "story": story,
        }


@dataclass
class ExcludedNode:
    """A node visited or pruned whose confidence fell below the threshold."""
    node_id: str
    kind: str
    file: Optional[str]
    distance: int
    confidence: float
    exclusion_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BlastRadiusReport:
    """Comprehensive, evidence-backed blast radius report."""
    target_id: str
    target_citation: Optional[str] = None
    found: bool = True
    direct: List[AffectedNode] = field(default_factory=list)
    indirect: List[AffectedNode] = field(default_factory=list)
    excluded: List[ExcludedNode] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    affected_tables: List[str] = field(default_factory=list)
    affected_configs: List[str] = field(default_factory=list)
    traversed_edges: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize report to a dictionary compatible with existing engine.impact() contracts.

        Node lists are compact (no per-hop paths) and capped, and the whole payload is
        trimmed to ``MAX_IMPACT_PAYLOAD_CHARS`` so hub nodes stay within the neighbors
        budget. The true counts are preserved in ``*_count`` and ``truncated``.
        """
        all_affected = [n for n in (self.direct + self.indirect) if not str(n.node_id).startswith("ext:")]
        cap = 25
        affected_nodes_dict = [n.to_dict() for n in all_affected[:cap]]
        # Also provide simplified fields matching legacy API
        for item in affected_nodes_dict:
            item["id"] = item["node_id"]
            item["depth"] = item["distance"]

        result: Dict[str, Any] = {
            "target": self.target_id,
            "target_citation": self.target_citation,
            "found": self.found,
            "affected_count": len(all_affected),
            "affected_nodes": affected_nodes_dict,
            "direct_count": len(self.direct),
            "indirect_count": len(self.indirect),
            "excluded_count": len(self.excluded),
            "direct": [n.to_dict() for n in self.direct[:15] if not str(n.node_id).startswith("ext:")],
            "indirect": [n.to_dict() for n in self.indirect[:15] if not str(n.node_id).startswith("ext:")],
            "excluded": [e.to_dict() for e in self.excluded[:10]],
            "affected_files": sorted(self.affected_files),
            "affected_tables": sorted(self.affected_tables),
            "affected_configs": sorted(self.affected_configs),
            "traversed_edges": self.traversed_edges[:20],
            "metrics": self.metrics,
            "truncated": len(all_affected) > cap,
        }

        # Hard budget guard: shed the lowest-value material (indirect → extra affected →
        # traversed edges → direct) until the serialized payload is within budget.
        def _too_big() -> bool:
            return len(json.dumps(result, default=str)) > MAX_IMPACT_PAYLOAD_CHARS

        while _too_big():
            if len(result["indirect"]) > 3:
                result["indirect"].pop()
            elif len(result["affected_nodes"]) > 5:
                result["affected_nodes"].pop()
            elif result["traversed_edges"]:
                result["traversed_edges"] = result["traversed_edges"][: max(0, len(result["traversed_edges"]) - 3)]
            elif len(result["direct"]) > 3:
                result["direct"].pop()
            else:
                break
            result["truncated"] = True

        return result


_EXCLUSION_CACHE: Dict[Tuple[str, Tuple[str, ...]], bool] = {}


def is_node_excluded(
    node_id: str,
    node_card: Optional[Any] = None,
    exclusions: Optional[Sequence[str]] = None,
) -> bool:
    """Check if a node ID or its associated file matches any exclusion rule.

    Supports:
    - Directory exclusions: 'shipping/', 'tests/shipping/', 'scripts/'
    - File exclusions: 'shipping.py', 'shipping/service.py', 'db/queries.sql'
    - Symbol exclusions: 'ShippingService', exact node_id, or symbol name
    - Glob-style path exclusions: '**/shipping/**', '*shipping*', 'tests/*'
    """
    if not exclusions:
        return False

    cache_key = (node_id, tuple(exclusions))
    if cache_key in _EXCLUSION_CACHE:
        return _EXCLUSION_CACHE[cache_key]

    file_path = ""
    if node_card and getattr(node_card, "span", None) and node_card.span.file:
        file_path = node_card.span.file.replace("\\", "/").strip()
    if not file_path:
        raw_id = node_id.replace("\\", "/")
        if "::" in raw_id:
            for part in raw_id.split("::"):
                if "/" in part or part.endswith((".py", ".ts", ".js", ".jsx", ".tsx", ".sql", ".sh", ".json", ".yaml", ".yml")):
                    file_path = part.strip()
                    break
        elif "/" in raw_id or raw_id.endswith((".py", ".ts", ".js", ".jsx", ".tsx", ".sql", ".sh", ".json", ".yaml", ".yml")):
            file_path = raw_id.strip()

    # Extract symbol name and parent symbol from node_id
    id_parts = node_id.split("::")
    symbol_name = id_parts[-1] if id_parts else node_id
    parent_symbol = id_parts[-2] if len(id_parts) > 1 else ""

    norm_file = "/" + file_path.lstrip("/") if file_path else ""

    for exc in exclusions:
        if not exc:
            continue
        exc_norm = exc.replace("\\", "/").strip()

        # 1. Exact node_id match
        if exc_norm == node_id:
            _EXCLUSION_CACHE[cache_key] = True
            return True

        # 2. Symbol name matching
        if exc_norm == symbol_name or exc_norm == parent_symbol:
            _EXCLUSION_CACHE[cache_key] = True
            return True
        if "." in symbol_name:
            sub_symbols = symbol_name.split(".")
            if exc_norm in sub_symbols:
                _EXCLUSION_CACHE[cache_key] = True
                return True

        # 3. Path matching
        if file_path:
            # Direct glob matching
            if fnmatch.fnmatch(file_path, exc_norm) or fnmatch.fnmatch(norm_file, exc_norm):
                _EXCLUSION_CACHE[cache_key] = True
                return True
            # Glob pattern with **
            if "**" in exc_norm:
                clean_pat = exc_norm.replace("**/", "*").replace("/**", "*")
                if fnmatch.fnmatch(file_path, clean_pat) or fnmatch.fnmatch(norm_file, clean_pat):
                    _EXCLUSION_CACHE[cache_key] = True
                    return True

            # Directory exclusion (trailing slash or directory segment)
            if exc_norm.endswith("/"):
                dir_name = exc_norm.rstrip("/")
                if f"/{dir_name}/" in f"{norm_file}/" or file_path.startswith(exc_norm) or file_path.startswith(dir_name + "/"):
                    _EXCLUSION_CACHE[cache_key] = True
                    return True
                if fnmatch.fnmatch(file_path, f"*{dir_name}/*"):
                    _EXCLUSION_CACHE[cache_key] = True
                    return True
            else:
                # Exact file path match or filename match
                if file_path == exc_norm or norm_file == "/" + exc_norm.lstrip("/"):
                    _EXCLUSION_CACHE[cache_key] = True
                    return True
                if file_path.endswith("/" + exc_norm) or file_path.endswith(exc_norm):
                    _EXCLUSION_CACHE[cache_key] = True
                    return True
                from pathlib import PurePosixPath
                if PurePosixPath(file_path).name == PurePosixPath(exc_norm).name and exc_norm.endswith(PurePosixPath(file_path).suffix):
                    _EXCLUSION_CACHE[cache_key] = True
                    return True
                # If exc_norm is a directory name without trailing slash
                path_segments = [p for p in file_path.split("/") if p]
                if exc_norm in path_segments:
                    _EXCLUSION_CACHE[cache_key] = True
                    return True

    _EXCLUSION_CACHE[cache_key] = False
    return False


def _format_node_citation(node_card: Any) -> Optional[str]:
    """Format file:start-end citation string for a node."""
    if not node_card or not node_card.span or not node_card.span.file:
        return None
    span = node_card.span
    if span.start == span.end:
        return f"{span.file}:{span.start}"
    return f"{span.file}:{span.start}-{span.end}"


def compute_blast_radius(
    graph: CanonicalGraph,
    target_id: str,
    max_depth: int = 5,
    direction: str = "both",
    confidence_threshold: float = 0.20,
    exclusions: Optional[Sequence[str]] = None,
) -> BlastRadiusReport:
    """Compute mathematical traversal confidence and evidence-backed blast radius.

    Args:
        graph: The CanonicalGraph to traverse.
        target_id: Exact identifier of the starting node.
        max_depth: Maximum traversal hop distance (default 5).
        direction: 'both', 'upstream', or 'downstream'.
        confidence_threshold: Minimum combined confidence for inclusion in indirect blast radius.
        exclusions: Optional collection of negative exclusion patterns (dirs, files, symbols, globs).

    Returns:
        BlastRadiusReport with partitioned direct, indirect, and excluded nodes.
    """
    target_node = graph.nodes.get(target_id)
    if not target_node:
        return BlastRadiusReport(target_id=target_id, found=False)

    target_citation = _format_node_citation(target_node)

    # Check if target itself matches an exclusion rule
    if exclusions and is_node_excluded(target_id, target_node, exclusions):
        return BlastRadiusReport(
            target_id=target_id,
            target_citation=target_citation,
            found=True,
            excluded=[
                ExcludedNode(
                    node_id=target_id,
                    kind=target_node.kind,
                    file=target_node.span.file if target_node.span else None,
                    distance=0,
                    confidence=1.0,
                    exclusion_reason="Target node matches explicit exclusion rule",
                )
            ],
            affected_files=[],
            affected_tables=[],
            affected_configs=[],
            metrics={"direct_count": 0, "indirect_count": 0, "excluded_count": 1},
        )

    # 1. Build adjacency maps (cached on graph)
    if hasattr(graph, "_cached_adj") and graph._cached_adj is not None:
        incoming_edges, outgoing_edges = graph._cached_adj
    else:
        incoming_edges: Dict[str, List[Edge]] = {}
        outgoing_edges: Dict[str, List[Edge]] = {}
        for edge in graph.edges:
            outgoing_edges.setdefault(edge.src, []).append(edge)
            incoming_edges.setdefault(edge.dst, []).append(edge)
        graph._cached_adj = (incoming_edges, outgoing_edges)

    # 2. Collect simple paths from target_id up to max_depth
    # State in queue: (current_node_id, current_path_of_steps, visited_nodes_in_path)
    node_paths: Dict[str, List[List[BlastRadiusStep]]] = {}
    node_min_dist: Dict[str, int] = {}
    traversed_edges_list: List[Dict[str, Any]] = []
    seen_edges: Set[Tuple[str, str, str, str]] = set()

    # Track hard-pruned excluded nodes
    explicit_excluded_nodes: List[ExcludedNode] = []
    explicit_excluded_ids: Set[str] = set()

    queue: deque = deque([(target_id, [], {target_id})])

    while queue:
        curr_id, current_steps, path_visited = queue.popleft()
        depth = len(current_steps)

        if depth >= max_depth:
            continue

        candidate_hops: List[Tuple[Edge, str, str]] = []
        if direction in ("both", "upstream"):
            for e in incoming_edges.get(curr_id, []):
                candidate_hops.append((e, e.src, "upstream"))
        if direction in ("both", "downstream"):
            for e in outgoing_edges.get(curr_id, []):
                candidate_hops.append((e, e.dst, "downstream"))

        curr_degree = len(incoming_edges.get(curr_id, [])) + len(outgoing_edges.get(curr_id, []))
        if depth >= 1 and curr_degree >= HIGH_DEGREE_THRESHOLD:
            continue
        if len(node_paths) >= MAX_EXPANSION_NODES:
            break

        candidate_hops.sort(
            key=lambda item: (
                _EDGE_EXPAND_PRIORITY.get(item[0].type.value, 20),
                item[1],
                item[2],
            )
        )
        if len(candidate_hops) > MAX_FANOUT:
            candidate_hops = candidate_hops[:MAX_FANOUT]

        for edge, next_id, flow_dir in candidate_hops:
            if len(traversed_edges_list) >= MAX_TRAVERSED_EDGES:
                break
            edge_key = (edge.src, edge.dst, edge.type.value, flow_dir)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                traversed_edges_list.append({
                    "src": edge.src,
                    "dst": edge.dst,
                    "type": edge.type.value,
                    "depth": depth + 1,
                    "flow": flow_dir,
                })

            if next_id in path_visited:
                continue

            conf_enum = edge.confidence.value if hasattr(edge.confidence, "value") else str(edge.confidence)

            src_lang = language_from_node_id(curr_id)
            dst_lang = language_from_node_id(next_id)
            if (
                edge.type not in _CROSS_LANG_EDGE_TYPES
                and src_lang
                and dst_lang
                and src_lang != dst_lang
            ):
                continue
            if not dst_lang and depth >= 1:
                continue

            step_prior = get_edge_prior(edge)
            step_citation = None
            if edge.evidence and edge.evidence.file:
                step_citation = f"{edge.evidence.file}:{edge.evidence.start_line}"
            elif next_id in graph.nodes:
                step_citation = _format_node_citation(graph.nodes[next_id])

            # Hard exclusion pruning: prune BEFORE adding to queue or recording paths
            next_node = graph.nodes.get(next_id)
            if exclusions and is_node_excluded(next_id, next_node, exclusions):
                if next_id not in explicit_excluded_ids:
                    explicit_excluded_ids.add(next_id)
                    explicit_excluded_nodes.append(ExcludedNode(
                        node_id=next_id,
                        kind=next_node.kind if next_node else "unknown",
                        file=next_node.span.file if next_node and next_node.span else None,
                        distance=depth + 1,
                        confidence=step_prior,
                        exclusion_reason="Explicit negative exclusion rule matched",
                    ))
                continue

            step = BlastRadiusStep(
                src=edge.src,
                dst=edge.dst,
                type=edge.type.value,
                confidence=step_prior,
                flow=flow_dir,
                citation=step_citation,
                how_derived=edge.evidence.how_derived if edge.evidence else None,
            )

            new_steps = current_steps + [step]
            node_paths.setdefault(next_id, []).append(new_steps)

            if next_id not in node_min_dist or depth + 1 < node_min_dist[next_id]:
                node_min_dist[next_id] = depth + 1

            expand = True
            if conf_enum.lower() in ("external", "unresolved"):
                expand = False
            if next_node and next_node.kind == "external_symbol":
                expand = False
            if expand and len(node_paths[next_id]) <= 3:
                queue.append((next_id, new_steps, path_visited | {next_id}))

    # 3. Compute mathematical confidence scores & partitions
    direct_nodes: List[AffectedNode] = []
    indirect_nodes: List[AffectedNode] = []
    excluded_nodes: List[ExcludedNode] = []

    affected_files: Set[str] = set()
    affected_tables: Set[str] = set()
    affected_configs: Set[str] = set()

    if target_node.span and target_node.span.file:
        affected_files.add(target_node.span.file)
    if is_sql_table_kind(target_node.kind):
        affected_tables.add(target_node.id.split("::")[-1])
    if is_config_kind(target_node.kind):
        affected_configs.add(target_node.id.split("::")[-1])

    for node_id, paths in node_paths.items():
        node = graph.nodes.get(node_id)
        kind = node.kind if node else "unknown"
        file_path = node.span.file if node and node.span else None
        citation = _format_node_citation(node) if node else None
        story_text = node.story.text if node and node.story else None
        distance = node_min_dist.get(node_id, 1)

        # Calculate path confidences
        path_objs: List[BlastRadiusPath] = []
        path_confidences: List[float] = []
        for p in paths:
            step_confs = [s.confidence for s in p]
            p_conf = calculate_path_confidence(step_confs)
            path_confidences.append(p_conf)
            path_objs.append(BlastRadiusPath(hops=p, path_confidence=p_conf))

        # Sort paths by confidence descending
        path_objs.sort(key=lambda x: x.path_confidence, reverse=True)

        # Combined multi-path confidence
        combined_conf = calculate_combined_confidence(path_confidences)
        graph_score = calculate_graph_score(combined_conf, distance)

        # Partitioning logic
        if combined_conf < confidence_threshold:
            excluded_nodes.append(ExcludedNode(
                node_id=node_id,
                kind=kind,
                file=file_path,
                distance=distance,
                confidence=combined_conf,
                exclusion_reason=f"Confidence score {combined_conf:.3f} is below minimum threshold ({confidence_threshold:.2f})",
            ))
            continue

        # Direct vs Indirect:
        # Direct: 1 hop away with combined confidence >= 0.50 (or high confidence >= 0.80)
        is_direct = (distance == 1 and combined_conf >= 0.50) or (combined_conf >= 0.80 and distance == 1)

        affected = AffectedNode(
            node_id=node_id,
            kind=kind,
            file=file_path,
            citation=citation,
            distance=distance,
            combined_confidence=combined_conf,
            graph_score=graph_score,
            category="direct" if is_direct else "indirect",
            paths=path_objs[:5],  # top 5 paths
            story=story_text,
        )

        if is_direct:
            direct_nodes.append(affected)
        else:
            indirect_nodes.append(affected)

        # Aggregate affected artifacts
        if file_path:
            affected_files.add(file_path)
        if is_sql_table_kind(kind):
            affected_tables.add(node_id.split("::")[-1])
        if is_config_kind(kind):
            affected_configs.add(node_id.split("::")[-1])

    # Merge explicit exclusions and confidence-pruned nodes
    all_excluded_nodes = explicit_excluded_nodes + excluded_nodes

    # Sort partitions by graph_score descending
    direct_nodes.sort(key=lambda n: (-n.graph_score, n.node_id))
    indirect_nodes.sort(key=lambda n: (-n.graph_score, n.node_id))
    all_excluded_nodes.sort(key=lambda e: (-e.confidence, e.node_id))
    direct_nodes = direct_nodes[:MAX_DIRECT_REPORT]
    indirect_nodes = indirect_nodes[:MAX_INDIRECT_REPORT]

    # Filter affected_files to ensure no excluded paths remain
    if exclusions:
        affected_files = {f for f in affected_files if not is_node_excluded(f, None, exclusions)}

    # 4. Summary metrics
    all_confs = [n.combined_confidence for n in direct_nodes + indirect_nodes]
    mean_conf = round(sum(all_confs) / len(all_confs), 4) if all_confs else 0.0
    max_dist = max([n.distance for n in direct_nodes + indirect_nodes], default=0)

    metrics = {
        "direct_count": len(direct_nodes),
        "indirect_count": len(indirect_nodes),
        "excluded_count": len(all_excluded_nodes),
        "mean_confidence": mean_conf,
        "max_distance": max_dist,
    }

    return BlastRadiusReport(
        target_id=target_id,
        target_citation=target_citation,
        found=True,
        direct=direct_nodes,
        indirect=indirect_nodes,
        excluded=all_excluded_nodes,
        affected_files=sorted(list(affected_files)),
        affected_tables=sorted(list(affected_tables)),
        affected_configs=sorted(list(affected_configs)),
        traversed_edges=traversed_edges_list,
        metrics=metrics,
    )
