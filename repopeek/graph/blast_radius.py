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
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from repopeek.models.schema import CanonicalGraph, Confidence, Edge, EdgeType


# ── Edge Prior Confidence Table ──
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
        d = asdict(self)
        d["confidence"] = self.combined_confidence
        return d


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
        """Serialize report to a dictionary compatible with existing engine.impact() contracts."""
        all_affected = self.direct + self.indirect
        affected_nodes_dict = [n.to_dict() for n in all_affected]
        # Also provide simplified fields matching legacy API
        for item in affected_nodes_dict:
            item["id"] = item["node_id"]
            item["depth"] = item["distance"]

        return {
            "target": self.target_id,
            "target_citation": self.target_citation,
            "found": self.found,
            "affected_count": len(all_affected),
            "affected_nodes": affected_nodes_dict,
            "direct_count": len(self.direct),
            "indirect_count": len(self.indirect),
            "excluded_count": len(self.excluded),
            "direct": [n.to_dict() for n in self.direct],
            "indirect": [n.to_dict() for n in self.indirect],
            "excluded": [e.to_dict() for e in self.excluded],
            "affected_files": sorted(self.affected_files),
            "affected_tables": sorted(self.affected_tables),
            "affected_configs": sorted(self.affected_configs),
            "traversed_edges": self.traversed_edges,
            "metrics": self.metrics,
        }


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
) -> BlastRadiusReport:
    """Compute mathematical traversal confidence and evidence-backed blast radius.

    Args:
        graph: The CanonicalGraph to traverse.
        target_id: Exact identifier of the starting node.
        max_depth: Maximum traversal hop distance (default 5).
        direction: 'both', 'upstream', or 'downstream'.
        confidence_threshold: Minimum combined confidence for inclusion in indirect blast radius.

    Returns:
        BlastRadiusReport with partitioned direct, indirect, and excluded nodes.
    """
    target_node = graph.nodes.get(target_id)
    if not target_node:
        return BlastRadiusReport(target_id=target_id, found=False)

    target_citation = _format_node_citation(target_node)

    # 1. Build adjacency maps
    incoming_edges: Dict[str, List[Edge]] = {}
    outgoing_edges: Dict[str, List[Edge]] = {}
    for edge in graph.edges:
        outgoing_edges.setdefault(edge.src, []).append(edge)
        incoming_edges.setdefault(edge.dst, []).append(edge)

    # 2. Collect simple paths from target_id up to max_depth
    # State in queue: (current_node_id, current_path_of_steps, visited_nodes_in_path)
    node_paths: Dict[str, List[List[BlastRadiusStep]]] = {}
    node_min_dist: Dict[str, int] = {}
    traversed_edges_list: List[Dict[str, Any]] = []
    seen_edges: Set[Tuple[str, str, str, str]] = set()

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

        for edge, next_id, flow_dir in candidate_hops:
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
                # Avoid cycles in this path
                continue

            step_prior = get_edge_prior(edge)
            step_citation = None
            if edge.evidence and edge.evidence.file:
                step_citation = f"{edge.evidence.file}:{edge.evidence.start_line}"
            elif next_id in graph.nodes:
                step_citation = _format_node_citation(graph.nodes[next_id])

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

            # Update shortest distance
            if next_id not in node_min_dist or depth + 1 < node_min_dist[next_id]:
                node_min_dist[next_id] = depth + 1

            # Bounded exploration: continue queue if paths to next_id < 10
            if len(node_paths[next_id]) <= 10:
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
    if "table" in target_node.id:
        affected_tables.add(target_node.id.split("::")[-1])
    if "config" in target_node.id or target_node.kind in ("json_config", "yaml_config"):
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
        if "table" in node_id:
            affected_tables.add(node_id.split("::")[-1])
        if "config" in node_id or kind in ("json_config", "yaml_config"):
            affected_configs.add(node_id.split("::")[-1])

    # Sort partitions by graph_score descending
    direct_nodes.sort(key=lambda n: n.graph_score, reverse=True)
    indirect_nodes.sort(key=lambda n: n.graph_score, reverse=True)
    excluded_nodes.sort(key=lambda e: e.confidence, reverse=True)

    # 4. Summary metrics
    all_confs = [n.combined_confidence for n in direct_nodes + indirect_nodes]
    mean_conf = round(sum(all_confs) / len(all_confs), 4) if all_confs else 0.0
    max_dist = max([n.distance for n in direct_nodes + indirect_nodes], default=0)

    metrics = {
        "direct_count": len(direct_nodes),
        "indirect_count": len(indirect_nodes),
        "excluded_count": len(excluded_nodes),
        "mean_confidence": mean_conf,
        "max_distance": max_dist,
    }

    return BlastRadiusReport(
        target_id=target_id,
        target_citation=target_citation,
        found=True,
        direct=direct_nodes,
        indirect=indirect_nodes,
        excluded=excluded_nodes,
        affected_files=sorted(list(affected_files)),
        affected_tables=sorted(list(affected_tables)),
        affected_configs=sorted(list(affected_configs)),
        traversed_edges=traversed_edges_list,
        metrics=metrics,
    )
