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

    def blast_radius(
        self,
        target_query: str,
        max_depth: int = 5,
        direction: str = "both",
        confidence_threshold: float = 0.20,
    ) -> Any:
        """Compute mathematical traversal confidence and evidence-backed blast radius."""
        from repopeek.graph.blast_radius import compute_blast_radius, BlastRadiusReport
        target = self.lookup(target_query)
        if not target:
            return BlastRadiusReport(target_id=target_query, found=False)

        return compute_blast_radius(
            self.graph,
            target.id,
            max_depth=max_depth,
            direction=direction,
            confidence_threshold=confidence_threshold,
        )

    def impact(
        self,
        target_query: str,
        max_depth: int = 5,
        direction: str = "both",
        confidence_threshold: float = 0.20,
    ) -> Dict[str, Any]:
        """Compute blast-radius tree answering 'If I change X, what breaks?'"""
        report = self.blast_radius(
            target_query,
            max_depth=max_depth,
            direction=direction,
            confidence_threshold=confidence_threshold,
        )
        return report.to_dict()

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

    def _build_node_index(self) -> Dict[str, Dict[str, Any]]:
        """Build a lightweight index dict for AST identifier search."""
        index: Dict[str, Dict[str, Any]] = {}
        for node_id, node in self.graph.nodes.items():
            index[node_id] = {
                "sig": node.sig,
                "story_text": node.story.text if node.story else None,
                "kind": node.kind,
                "file": node.span.file if node.span else None,
            }
        return index

    def resolve_task(
        self,
        task: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Resolve a natural language engineering task to ranked candidate symbols.

        Uses three-stage hybrid retrieval:
        1. AST identifier extraction and variant matching (always available)
        2. SQLite FTS5 BM25 retrieval (if cache.db exists with FTS5 table)
        3. Reciprocal Rank Fusion (k=60) combining both sources

        Args:
            task: Natural language task description.
            limit: Maximum number of candidates to return.

        Returns:
            List of dicts with keys: node_id, score, reasons, node_card (serialized).
        """
        from repopeek.retrieval.intent import (
            SymbolCandidate,
            extract_task_identifiers,
            resolve_task_to_symbols,
            _build_fts_query,
        )

        # Build lightweight index for AST search
        node_index = self._build_node_index()

        # Attempt FTS5 BM25 retrieval if SQLite cache is available
        fts_results = None
        if self.storage_dir:
            db_path = self.storage_dir / "cache.db"
            if db_path.exists():
                from repopeek.storage.sqlite_cache import query_fts5_bm25

                intent = extract_task_identifiers(task)
                fts_query = _build_fts_query(intent)
                if fts_query:
                    fts_results = query_fts5_bm25(db_path, fts_query, limit=50)

        # Run the full resolution pipeline
        candidates = resolve_task_to_symbols(
            task=task,
            node_index=node_index,
            fts_results=fts_results,
            limit=limit,
        )

        # Enrich with node card data
        results: List[Dict[str, Any]] = []
        for candidate in candidates:
            node = self.graph.nodes.get(candidate.node_id)
            result: Dict[str, Any] = {
                "node_id": candidate.node_id,
                "score": candidate.score,
                "reasons": candidate.reasons,
            }
            if node:
                result["kind"] = node.kind
                result["sig"] = node.sig
                result["file"] = node.span.file if node.span else None
                result["story"] = node.story.text if node.story else None
            results.append(result)

        return results

    def compile_context(
        self,
        task: str,
        budget: int = 1500,
        level: int = 2,
        include_snippets: bool = True,
    ) -> Any:
        """Compile a natural language engineering task into a ContextPackage."""
        from repopeek.context import ContextCompiler
        compiler = ContextCompiler(self)
        return compiler.compile(task=task, budget=budget, level=level, include_snippets=include_snippets)

    def change_plan(self, task: str) -> Any:
        """Generate a risk-assessed, step-by-step engineering change plan."""
        from repopeek.context import ContextCompiler
        compiler = ContextCompiler(self)
        pkg = compiler.compile(task=task)
        return pkg.change_plan

    def co_changes(self, target_query: str) -> List[Dict[str, Any]]:
        """Query historical git co-change relationships for target file or symbol."""
        from repopeek.temporal.miner import GitTemporalMiner
        miner = GitTemporalMiner(repo_root=self.repo_root)
        relations = miner.compute_co_changes()

        target_file = None
        target_card = self.lookup(target_query)
        if target_card and target_card.span:
            target_file = target_card.span.file
        else:
            norm_q = target_query.replace("\\", "/").lstrip("./")
            for nid, node in self.graph.nodes.items():
                if node.span and (node.span.file == norm_q or node.span.file.endswith(norm_q)):
                    target_file = node.span.file
                    break

        if not target_file:
            target_file = target_query.replace("\\", "/").lstrip("./")

        results = []
        for r in relations:
            if r.file_a == target_file or target_file.endswith(r.file_a):
                results.append({
                    "target_file": r.file_a,
                    "co_changed_file": r.file_b,
                    "probability": r.probability,
                    "co_commit_count": r.co_commit_count,
                    "total_commits": r.total_commits_a,
                    "last_co_commit_age_days": r.last_co_commit_age_days,
                })
        return results

    def http_routes(self) -> Dict[str, Any]:
        """Discover server HTTP route endpoints, client calls, and cross-boundary linkages."""
        from repopeek.bridges.http import HttpBoundaryBridge
        bridge = HttpBoundaryBridge()
        server_routes = bridge.extract_server_routes(self.graph)
        client_calls = bridge.extract_client_calls(self.graph)
        resolved_edges = bridge.resolve_and_link(self.graph)

        routes_data = [
            {
                "method": r.method,
                "path": r.raw_path,
                "norm_path": r.norm_path,
                "node_id": r.node_id,
                "file": r.file,
                "line": r.line,
            }
            for r in server_routes
        ]

        calls_data = [
            {
                "caller_node_id": c.caller_node_id,
                "method": c.method,
                "url": c.raw_url,
                "norm_path": c.norm_path,
                "file": c.file,
                "line": c.line,
            }
            for c in client_calls
        ]

        links_data = [
            {
                "client_id": e.src,
                "server_id": e.dst,
                "evidence": e.evidence.how_derived if e.evidence else "",
                "file": e.evidence.file if e.evidence else "",
            }
            for e in resolved_edges
        ]

        return {
            "routes": routes_data,
            "calls": calls_data,
            "links": links_data,
            "total_routes": len(routes_data),
            "total_calls": len(calls_data),
            "total_links": len(links_data),
        }


