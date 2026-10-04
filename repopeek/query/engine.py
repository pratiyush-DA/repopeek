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
        repo_root: Optional[Path] = None,
    ) -> None:
        if graph is not None:
            self.graph = graph
        elif storage_dir is not None:
            self.graph = load_canonical_graph(storage_dir)
        else:
            raise ValueError("Either 'graph' or 'storage_dir' must be provided to GraphQueryEngine.")

        self.storage_dir = Path(storage_dir).resolve() if storage_dir else None
        if repo_root:
            self.repo_root = Path(repo_root).resolve()
        elif self.storage_dir:
            self.repo_root = self.storage_dir.parent if self.storage_dir.name in (".repopeek", "output") else self.storage_dir
        else:
            self.repo_root = Path(".").resolve()

        # Precompute indexed lookups
        self._incoming_edges: Dict[str, List[Any]] = {}
        self._outgoing_edges: Dict[str, List[Any]] = {}

        for edge in self.graph.edges:
            self._incoming_edges.setdefault(edge.dst, []).append(edge)
            self._outgoing_edges.setdefault(edge.src, []).append(edge)

    def compute_blast(self, node_id: str) -> Dict[str, int]:
        """Compute compact 1-hop blast metrics (callers, readers, files, tables)."""
        inc = self._incoming_edges.get(node_id, [])
        callers = 0
        readers = 0
        files = set()
        tables = set()

        for e in inc:
            etype = e.type.value if hasattr(e.type, "value") else str(e.type)
            if etype == "CALLS":
                callers += 1
            elif etype == "READS":
                readers += 1

            if e.src in self.graph.nodes:
                src_node = self.graph.nodes[e.src]
                if src_node.span and src_node.span.file:
                    files.add(src_node.span.file)
                if "table" in src_node.kind.lower() or "entity" in src_node.kind.lower():
                    tables.add(src_node.id)

        return {
            "callers": callers,
            "readers": readers,
            "files": len(files),
            "tables": len(tables),
        }

    def extract_snippet(self, node: NodeCard, max_lines: int = 15) -> Optional[str]:
        """Extract physical code snippet from disk corresponding to node span."""
        if not node.span or not node.span.file:
            return None

        candidates = [
            Path(node.span.file),
            self.repo_root / node.span.file if self.repo_root else None,
            Path(".") / node.span.file,
            Path(__file__).parent.parent.parent / "tests" / "fixtures" / "sample_repo" / node.span.file,
        ]
        target_path = None
        for c in candidates:
            if c and c.exists() and c.is_file():
                target_path = c
                break

        if not target_path:
            return None

        try:
            lines = target_path.read_text(encoding="utf-8", errors="replace").splitlines()
            start_idx = max(0, node.span.start - 1)
            end_idx = min(len(lines), node.span.end)

            span_lines = lines[start_idx:end_idx]
            if not span_lines:
                return None

            if len(span_lines) > max_lines:
                truncated = span_lines[:max_lines]
                truncated.append(f"# ... ({len(span_lines) - max_lines} lines truncated)")
                return "\n".join(truncated)
            return "\n".join(span_lines)
        except Exception:
            return None

    def lookup(
        self,
        query: str,
        include_snippet: bool = False,
        include_blast: bool = True,
    ) -> Optional[NodeCard]:
        """Lookup node card by exact ID, qualified symbol name, or identifier suffix."""
        target: Optional[NodeCard] = None
        if query in self.graph.nodes:
            target = self.graph.nodes[query]
        else:
            # Suffix matching
            matches = [
                node for nid, node in self.graph.nodes.items()
                if nid.endswith(f"::{query}") or nid.endswith(f".{query}") or nid == query
            ]
            if matches:
                target = matches[0]
            else:
                # Substring search
                substr_matches = [
                    node for nid, node in self.graph.nodes.items()
                    if query in nid
                ]
                if substr_matches:
                    target = substr_matches[0]

        if not target:
            return None

        card = target.model_copy()
        if include_blast and card.blast is None:
            card.blast = self.compute_blast(card.id)
        if include_snippet and card.snippet is None:
            card.snippet = self.extract_snippet(card)

        return card

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

    def context_pack(
        self,
        targets: List[str],
        token_budget: int = 1500,
        include_snippet: bool = False,
    ) -> ContextPack:
        """Produce minimal, budget-governed sub-graph pack for low-context AI coding agents."""
        resolved_targets: List[NodeCard] = []
        for t in targets:
            node = self.lookup(t, include_snippet=include_snippet, include_blast=True)
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
            if card_dict.get("blast") is None:
                card_dict["blast"] = self.compute_blast(t_node.id)
            if include_snippet and not card_dict.get("snippet"):
                snip = self.extract_snippet(t_node)
                if snip:
                    card_dict["snippet"] = snip
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
