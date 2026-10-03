"""High-performance graph query engine providing lookup, impact, data trace, and context packs."""

from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from repopeek.models.schema import CanonicalGraph, EdgeType, NodeCard
from repopeek.query.pack import ContextPack
from repopeek.storage.json_store import load_canonical_graph


class GraphQueryEngine:
    """Query and traversal engine executing low-context intelligence queries."""

    def __init__(
        self,
        graph: Optional[CanonicalGraph] = None,
        storage_dir: Optional[Path] = None,
    ) -> None:
        if graph is not None:
            self.graph = graph
        elif storage_dir is not None:
            self.graph = load_canonical_graph(storage_dir)
        else:
            raise ValueError("Either 'graph' or 'storage_dir' must be provided to GraphQueryEngine.")

        # Precompute indexed lookups
        self._incoming_edges: Dict[str, List[Any]] = {}
        self._outgoing_edges: Dict[str, List[Any]] = {}

        for edge in self.graph.edges:
            self._incoming_edges.setdefault(edge.dst, []).append(edge)
            self._outgoing_edges.setdefault(edge.src, []).append(edge)

    def lookup(self, query: str) -> Optional[NodeCard]:
        """Lookup node card by exact ID, qualified symbol name, or identifier suffix."""
        if query in self.graph.nodes:
            return self.graph.nodes[query]

        # Suffix matching
        matches = [
            node for nid, node in self.graph.nodes.items()
            if nid.endswith(f"::{query}") or nid.endswith(f".{query}") or nid == query
        ]
        if matches:
            return matches[0]

        # Substring search
        substr_matches = [
            node for nid, node in self.graph.nodes.items()
            if query in nid
        ]
        return substr_matches[0] if substr_matches else None

    def search(self, query: str, limit: int = 10) -> List[NodeCard]:
        """Search node cards matching query across ID, signature, or story text."""
        q = query.lower()
        results: List[NodeCard] = []

        for node in self.graph.nodes.values():
            id_match = q in node.id.lower()
            sig_match = node.sig is not None and q in node.sig.lower()
            story_match = node.story is not None and q in node.story.text.lower()

            if id_match or sig_match or story_match:
                results.append(node)
                if len(results) >= limit:
                    break

        return results

    def neighbors(self, node_id: str, direction: str = "both") -> Dict[str, Any]:
        """Inspect inbound and outbound relational edges connected to a node."""
        node = self.lookup(node_id)
        if not node:
            return {"node": None, "incoming": [], "outgoing": []}

        resolved_id = node.id
        incoming = []
        outgoing = []

        if direction in ("both", "incoming", "upstream"):
            for e in self._incoming_edges.get(resolved_id, []):
                incoming.append({
                    "src": e.src,
                    "dst": e.dst,
                    "type": e.type.value,
                    "confidence": e.confidence.value,
                    "src_card": self.graph.nodes[e.src].model_dump(exclude_none=True)
                    if e.src in self.graph.nodes else None,
                })

        if direction in ("both", "outgoing", "downstream"):
            for e in self._outgoing_edges.get(resolved_id, []):
                outgoing.append({
                    "src": e.src,
                    "dst": e.dst,
                    "type": e.type.value,
                    "confidence": e.confidence.value,
                    "dst_card": self.graph.nodes[e.dst].model_dump(exclude_none=True)
                    if e.dst in self.graph.nodes else None,
                })

        return {
            "node": node.model_dump(exclude_none=True),
            "incoming": incoming,
            "outgoing": outgoing,
        }

    def impact(
        self,
        target_query: str,
        max_depth: int = 5,
        direction: str = "both",
    ) -> Dict[str, Any]:
        """Compute blast-radius tree answering 'If I change X, what breaks?'"""
        target = self.lookup(target_query)
        if not target:
            return {"target": target_query, "found": False, "affected_nodes": [], "affected_files": [], "affected_tables": [], "affected_configs": []}

        target_id = target.id
        queue: deque = deque([(target_id, 0)])
        visited: Set[str] = {target_id}

        affected_nodes: List[Dict[str, Any]] = []
        traversed_edges: List[Dict[str, Any]] = []
        affected_files: Set[str] = set()
        affected_tables: Set[str] = set()
        affected_configs: Set[str] = set()

        if target.span and target.span.file:
            affected_files.add(target.span.file)
        if "table" in target.id:
            affected_tables.add(target.id.split("::")[-1])
        if "config" in target.id or target.kind in ("json_config", "yaml_config"):
            affected_configs.add(target.id.split("::")[-1])

        while queue:
            curr_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            edges_to_traverse = []
            if direction in ("both", "upstream"):
                for e in self._incoming_edges.get(curr_id, []):
                    edges_to_traverse.append((e, e.src, "upstream"))
            if direction in ("both", "downstream"):
                for e in self._outgoing_edges.get(curr_id, []):
                    edges_to_traverse.append((e, e.dst, "downstream"))

            for edge, next_id, flow_dir in edges_to_traverse:
                traversed_edges.append({
                    "src": edge.src,
                    "dst": edge.dst,
                    "type": edge.type.value,
                    "depth": depth + 1,
                    "flow": flow_dir,
                })

                if next_id not in visited:
                    visited.add(next_id)
                    next_node = self.graph.nodes.get(next_id)
                    if next_node:
                        if next_node.span and next_node.span.file:
                            affected_files.add(next_node.span.file)
                        if "table" in next_node.id:
                            affected_tables.add(next_node.id.split("::")[-1])
                        if "config" in next_node.id or next_node.kind in ("json_config", "yaml_config"):
                            affected_configs.add(next_node.id.split("::")[-1])

                        affected_nodes.append({
                            "id": next_node.id,
                            "kind": next_node.kind,
                            "depth": depth + 1,
                            "story": next_node.story.text if next_node.story else None,
                            "file": next_node.span.file if next_node.span else None,
                        })
                    queue.append((next_id, depth + 1))

        return {
            "target": target_id,
            "found": True,
            "affected_count": len(affected_nodes),
            "affected_nodes": affected_nodes,
            "traversed_edges": traversed_edges,
            "affected_files": sorted(list(affected_files)),
            "affected_tables": sorted(list(affected_tables)),
            "affected_configs": sorted(list(affected_configs)),
        }

    def data_trace(self, entity_query: str) -> Dict[str, Any]:
        """Trace variable def-use and data entity flows across language barriers."""
        entity = self.lookup(entity_query)
        entity_id = entity.id if entity else entity_query

        writers = []
        readers = []

        for e in self.graph.edges:
            if e.dst == entity_id or entity_query in e.dst:
                if e.type == EdgeType.WRITES:
                    writers.append({
                        "writer_id": e.src,
                        "file": self.graph.nodes[e.src].span.file
                        if e.src in self.graph.nodes and self.graph.nodes[e.src].span else None,
                        "story": self.graph.nodes[e.src].story.text
                        if e.src in self.graph.nodes and self.graph.nodes[e.src].story else None,
                    })
                elif e.type == EdgeType.READS:
                    readers.append({
                        "reader_id": e.src,
                        "file": self.graph.nodes[e.src].span.file
                        if e.src in self.graph.nodes and self.graph.nodes[e.src].span else None,
                        "story": self.graph.nodes[e.src].story.text
                        if e.src in self.graph.nodes and self.graph.nodes[e.src].story else None,
                    })

        return {
            "entity": entity_id,
            "writers_count": len(writers),
            "readers_count": len(readers),
            "writers": writers,
            "readers": readers,
        }

    def context_pack(self, targets: List[str], token_budget: int = 1500) -> ContextPack:
        """Produce minimal, budget-governed sub-graph pack for low-context AI coding agents."""
        resolved_targets: List[NodeCard] = []
        for t in targets:
            node = self.lookup(t)
            if node:
                resolved_targets.append(node)

        packed_nodes: Dict[str, Dict[str, Any]] = {}
        packed_edges: List[Dict[str, Any]] = []
        affected_files: Set[str] = set()
        affected_tables: Set[str] = set()

        # Helper to compute estimated tokens
        def current_tokens() -> int:
            mock_pack = ContextPack(
                targets=targets,
                nodes=list(packed_nodes.values()),
                relationships=packed_edges,
                affected_files=list(affected_files),
                affected_tables=list(affected_tables),
            )
            return ContextPack.estimate_tokens_from_text(mock_pack.to_markdown())

        # 1. First priority: Target nodes
        for t_node in resolved_targets:
            card_dict = t_node.model_dump(exclude_none=True)
            packed_nodes[t_node.id] = card_dict
            if t_node.span and t_node.span.file:
                affected_files.add(t_node.span.file)
            if "table" in t_node.id:
                affected_tables.add(t_node.id.split("::")[-1])

        # 2. Second priority: Direct 1-hop neighbors of targets
        candidate_neighbors: List[NodeCard] = []
        for t_node in resolved_targets:
            for e in self._incoming_edges.get(t_node.id, []):
                packed_edges.append({
                    "src": e.src, "dst": e.dst, "type": e.type.value, "confidence": e.confidence.value
                })
                if e.src in self.graph.nodes and e.src not in packed_nodes:
                    candidate_neighbors.append(self.graph.nodes[e.src])

            for e in self._outgoing_edges.get(t_node.id, []):
                packed_edges.append({
                    "src": e.src, "dst": e.dst, "type": e.type.value, "confidence": e.confidence.value
                })
                if e.dst in self.graph.nodes and e.dst not in packed_nodes:
                    candidate_neighbors.append(self.graph.nodes[e.dst])

        for c_node in candidate_neighbors:
            if c_node.id in packed_nodes:
                continue
            card_dict = c_node.model_dump(exclude_none=True)
            packed_nodes[c_node.id] = card_dict
            if c_node.span and c_node.span.file:
                affected_files.add(c_node.span.file)
            if "table" in c_node.id:
                affected_tables.add(c_node.id.split("::")[-1])

            if current_tokens() > token_budget:
                del packed_nodes[c_node.id]
                break

        # 3. Third priority: Upstream impact callers
        for t_node in resolved_targets:
            impact_res = self.impact(t_node.id, max_depth=3)
            for imp in impact_res.get("affected_nodes", []):
                imp_id = imp["id"]
                if imp_id not in packed_nodes and imp_id in self.graph.nodes:
                    imp_card = self.graph.nodes[imp_id].model_dump(exclude_none=True)
                    packed_nodes[imp_id] = imp_card
                    if current_tokens() > token_budget:
                        del packed_nodes[imp_id]
                        break

        # Deduplicate relationships
        seen_edges = set()
        dedup_edges = []
        for e in packed_edges:
            pair = (e["src"], e["dst"], e["type"])
            if pair not in seen_edges and e["src"] in packed_nodes and e["dst"] in packed_nodes:
                seen_edges.add(pair)
                dedup_edges.append(e)

        final_pack = ContextPack(
            targets=targets,
            token_budget=token_budget,
            nodes=list(packed_nodes.values()),
            relationships=dedup_edges,
            affected_files=sorted(list(affected_files)),
            affected_tables=sorted(list(affected_tables)),
        )
        final_pack.estimated_tokens = ContextPack.estimate_tokens_from_text(final_pack.to_markdown())
        return final_pack
