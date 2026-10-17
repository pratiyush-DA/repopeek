"""High-performance graph query engine providing lookup, impact, data trace, and context packs."""

import re
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from repopeek.graph.identity import is_sql_table_kind
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

        # Precomputed analytics & temporal cache for sub-millisecond query performance
        self._precomputed_analytics: Dict[str, Any] = {}
        self._cached_co_changes: Optional[List[Any]] = None
        if self.storage_dir:
            analytics_file = self.storage_dir / "analytics.json"
            if analytics_file.exists():
                try:
                    import json
                    self._precomputed_analytics = json.loads(analytics_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            elif (self.storage_dir / "cache.db").exists():
                try:
                    from repopeek.storage.sqlite_cache import query_sqlite_analytics
                    for k in ("communities", "god_nodes", "cycles"):
                        val = query_sqlite_analytics(self.storage_dir / "cache.db", k)
                        if val is not None:
                            self._precomputed_analytics[k] = val
                except Exception:
                    pass

            co_file = self.storage_dir / "co_changes.json"
            if co_file.exists():
                try:
                    import json
                    self._cached_co_changes = json.loads(co_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

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
                if is_sql_table_kind(src_node.kind):
                    tables.add(src_node.id)

        return {
            "callers": callers,
            "readers": readers,
            "files": len(files),
            "tables": len(tables),
        }

    def extract_snippet(self, node: NodeCard, max_lines: int = 40, max_chars: int = 2000) -> Optional[str]:
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
                text = "\n".join(truncated)
            else:
                text = "\n".join(span_lines)
            if len(text) > max_chars:
                return text[:max_chars] + "\n# ... (truncated)"
            return text
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
        limit = 30

        def _edge_brief(e: Any, peer: str) -> Dict[str, Any]:
            peer_node = self.graph.nodes.get(peer)
            return {
                "src": e.src,
                "dst": e.dst,
                "type": e.type.value,
                "confidence": e.confidence.value,
                "peer_id": peer,
                "peer_kind": peer_node.kind if peer_node else None,
                "peer_file": peer_node.span.file if peer_node and peer_node.span else None,
            }

        if direction in ("both", "incoming", "upstream"):
            for e in self._incoming_edges.get(resolved_id, [])[:limit]:
                incoming.append(_edge_brief(e, e.src))

        if direction in ("both", "outgoing", "downstream"):
            for e in self._outgoing_edges.get(resolved_id, [])[:limit]:
                outgoing.append(_edge_brief(e, e.dst))

        return {
            "node": {
                "id": node.id,
                "kind": node.kind,
                "sig": node.sig,
                "file": node.span.file if node.span else None,
            },
            "incoming": incoming,
            "outgoing": outgoing,
            "truncated": (
                len(self._incoming_edges.get(resolved_id, [])) > limit
                or len(self._outgoing_edges.get(resolved_id, [])) > limit
            ),
        }

    def blast_radius(
        self,
        target_query: str,
        max_depth: int = 5,
        direction: str = "both",
        confidence_threshold: float = 0.20,
        exclusions: Optional[Sequence[str]] = None,
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
            exclusions=exclusions,
        )

    def impact(
        self,
        target_query: str,
        max_depth: int = 5,
        direction: str = "both",
        confidence_threshold: float = 0.20,
        exclusions: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """Compute blast-radius tree answering 'If I change X, what breaks?'"""
        report = self.blast_radius(
            target_query,
            max_depth=max_depth,
            direction=direction,
            confidence_threshold=confidence_threshold,
            exclusions=exclusions,
        )
        return report.to_dict()

    def data_trace(self, entity_query: str) -> Dict[str, Any]:
        """Trace variable def-use and data entity flows across language barriers."""
        entity = self.lookup(entity_query)
        entity_id = entity.id if entity else entity_query
        eq_clean = entity_query.strip()
        eq_lower = eq_clean.lower()

        # Token pattern to avoid matching substring inside other identifiers (e.g. 'confidence' vs '_calculate_confidence')
        token_pat = re.compile(rf"(?:^|[.:/]){re.escape(eq_lower)}(?:$|[.:])", re.IGNORECASE)

        def _is_entity_match(dst: str) -> bool:
            dst_lower = dst.lower()
            if dst_lower == entity_id.lower() or dst_lower == eq_lower:
                return True
            if dst_lower.endswith(f"::{eq_lower}") or dst_lower.endswith(f":{eq_lower}") or dst_lower.endswith(f".{eq_lower}"):
                return True
            if token_pat.search(dst):
                return True
            return False

        writers = []
        readers = []
        seen_writers: Set[str] = set()
        seen_readers: Set[str] = set()

        for e in self.graph.edges:
            if _is_entity_match(e.dst):
                if e.type == EdgeType.WRITES:
                    if e.src not in seen_writers:
                        seen_writers.add(e.src)
                        node = self.graph.nodes.get(e.src)
                        writers.append({
                            "writer_id": e.src,
                            "file": node.span.file if node and node.span else None,
                            "sig": node.sig if node and node.sig else None,
                            "story": node.story.text if node and node.story else None,
                        })
                elif e.type == EdgeType.READS:
                    if e.src not in seen_readers:
                        seen_readers.add(e.src)
                        node = self.graph.nodes.get(e.src)
                        readers.append({
                            "reader_id": e.src,
                            "file": node.span.file if node and node.span else None,
                            "sig": node.sig if node and node.sig else None,
                            "story": node.story.text if node and node.story else None,
                        })

        result = {
            "entity": entity_id,
            "writers_count": len(writers),
            "readers_count": len(readers),
            "writers": writers[:30],
            "readers": readers[:30],
        }
        if not writers and not readers:
            result["note"] = (
                f"No reads/writes found for '{entity_query}'. It may not be a tracked data "
                "entity, table, or variable in this graph (try repopeek_lookup or repopeek_resolve)."
            )
        return result

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
            if is_sql_table_kind(t_node.kind):
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

        def _neighbor_key(n: NodeCard) -> tuple:
            k = n.kind.lower()
            if k in ("function", "method", "class"):
                pri = 0
            elif k in ("sql_table", "sql_query"):
                pri = 1
            elif k in ("yaml_config", "json_config", "external_symbol", "file", "module"):
                pri = 4
            else:
                pri = 2
            return (pri, n.id)

        candidate_neighbors.sort(key=_neighbor_key)
        packed_neighbor_count = 0
        for c_node in candidate_neighbors:
            if c_node.id in packed_nodes:
                continue
            if c_node.kind == "external_symbol":
                continue
            card_dict = c_node.model_dump(exclude_none=True)
            packed_nodes[c_node.id] = card_dict
            if c_node.span and c_node.span.file:
                affected_files.add(c_node.span.file)
            if is_sql_table_kind(c_node.kind):
                affected_tables.add(c_node.id.split("::")[-1])
            packed_neighbor_count += 1
            if packed_neighbor_count >= 12 or current_tokens() > token_budget:
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
        if hasattr(self, "_cached_node_index") and self._cached_node_index is not None:
            return self._cached_node_index
        index: Dict[str, Dict[str, Any]] = {}
        for node_id, node in self.graph.nodes.items():
            index[node_id] = {
                "sig": node.sig,
                "story_text": node.story.text if node.story else None,
                "kind": node.kind,
                "file": node.span.file if node.span else None,
            }
        self._cached_node_index = index
        return index

    def resolve_task(
        self,
        task: str,
        limit: int = 5,
        enable_stemming: bool = True,
        enable_compounds: bool = True,
        use_rrf_scoring: bool = False,
        include_story: bool = False,
    ) -> List[Dict[str, Any]]:
        """Resolve a natural language engineering task to ranked candidate symbols.

        Uses calibrated multi-component hybrid retrieval (AST + BM25 + Ranking).
        Defaults to a lean, token-efficient payload (top 5 candidates).

        Args:
            task: Natural language task description.
            limit: Maximum number of candidates to return (default: 5).
            enable_stemming: Whether to apply conservative linguistic stemming.
            enable_compounds: Whether to generate adjacent compound variants.
            use_rrf_scoring: Whether to fallback to baseline pure RRF ranking.
            include_story: Whether to serialize full narrative stories (default: False).

        Returns:
            List of dicts with keys: node_id, score, reasons, kind, sig, file, (optional story).
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
            enable_stemming=enable_stemming,
            enable_compounds=enable_compounds,
            use_rrf_scoring=use_rrf_scoring,
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
                if include_story and node.story:
                    result["story"] = node.story.text
            results.append(result)

        return results

    def compile_context(
        self,
        task: str,
        budget: int = 1500,
        level: int = 2,
        include_snippets: bool = True,
        exclusions: Optional[Sequence[str]] = None,
    ) -> Any:
        """Compile a natural language engineering task into a ContextPackage."""
        from repopeek.context import ContextCompiler
        compiler = ContextCompiler(self)
        return compiler.compile(
            task=task,
            budget=budget,
            level=level,
            include_snippets=include_snippets,
            exclusions=exclusions,
        )

    def explain(self, task: str, limit: int = 5) -> str:
        """Deterministic query and retrieval explain report."""
        from repopeek.retrieval.intent import (
            explain_task,
            format_explain,
            extract_task_identifiers,
            _build_fts_query,
        )
        fts_results = None
        if self.storage_dir:
            db_path = self.storage_dir / "cache.db"
            if db_path.exists():
                from repopeek.storage.sqlite_cache import query_fts5_bm25
                intent = extract_task_identifiers(task)
                fts_query = _build_fts_query(intent)
                if fts_query:
                    fts_results = query_fts5_bm25(db_path, fts_query, limit=50)

        node_index = self._build_node_index()
        report = explain_task(task, node_index=node_index, fts_results=fts_results, limit=limit)
        return format_explain(report)

    def change_plan(self, task: str) -> Any:
        """Generate a risk-assessed, step-by-step engineering change plan."""
        from repopeek.context import ContextCompiler
        compiler = ContextCompiler(self)
        pkg = compiler.compile(task=task)
        return pkg.change_plan

    def get_communities(
        self, resolution: float = 1.0
    ) -> Tuple[Dict[int, List[str]], Dict[int, str]]:
        """Retrieve modular communities, utilizing precomputed cache for sub-millisecond retrieval."""
        if resolution == 1.0 and "communities" in self._precomputed_analytics:
            raw = self._precomputed_analytics["communities"]
            comms = {int(k): v for k, v in raw.get("communities", {}).items()}
            labels = {int(k): v for k, v in raw.get("labels", {}).items()}
            return comms, labels

        from repopeek.graph.clustering import detect_communities, generate_community_labels
        comms = detect_communities(self.graph, resolution=resolution)
        labels = generate_community_labels(self.graph, comms)
        if resolution == 1.0:
            self._precomputed_analytics["communities"] = {
                "communities": {str(k): v for k, v in comms.items()},
                "labels": {str(k): v for k, v in labels.items()},
            }
        return comms, labels

    def get_god_nodes(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Retrieve highest centrality god nodes, using precomputed cache when available."""
        if "god_nodes" in self._precomputed_analytics:
            return self._precomputed_analytics["god_nodes"][:top_n]

        from repopeek.graph.analysis import god_nodes
        gods = god_nodes(self.graph, top_n=max(top_n, 30))
        self._precomputed_analytics["god_nodes"] = gods
        return gods[:top_n]

    def get_cycles(self) -> List[Dict[str, Any]]:
        """Retrieve code import cycles, using precomputed cache when available."""
        if "cycles" in self._precomputed_analytics:
            return self._precomputed_analytics["cycles"]

        from repopeek.graph.analysis import find_import_cycles
        cycles = find_import_cycles(self.graph)
        self._precomputed_analytics["cycles"] = cycles
        return cycles

    def co_changes(self, target_query: str) -> List[Dict[str, Any]]:
        """Query historical git co-change relationships for target file or symbol."""
        if self._cached_co_changes is None:
            if self.storage_dir and (self.storage_dir / "co_changes.json").exists():
                try:
                    import json
                    self._cached_co_changes = json.loads(
                        (self.storage_dir / "co_changes.json").read_text(encoding="utf-8")
                    )
                except Exception:
                    pass

            if self._cached_co_changes is None:
                from repopeek.temporal.miner import GitTemporalMiner
                miner = GitTemporalMiner(repo_root=self.repo_root)
                self._cached_co_changes = [
                    {
                        "target_file": r.file_a,
                        "co_changed_file": r.file_b,
                        "probability": r.probability,
                        "co_commit_count": r.co_commit_count,
                        "total_commits": r.total_commits_a,
                        "last_co_commit_age_days": r.last_co_commit_age_days,
                    }
                    for r in miner.compute_co_changes()
                ]

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
        for r in (self._cached_co_changes or []):
            f_a = r.get("target_file", "")
            if f_a == target_file or target_file.endswith(f_a):
                results.append(r)
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

        result = {
            "routes": routes_data[:40],
            "calls": calls_data[:40],
            "links": links_data[:40],
            "total_routes": len(routes_data),
            "total_calls": len(calls_data),
            "total_links": len(links_data),
        }
        if not routes_data and not links_data:
            result["note"] = (
                "No HTTP routes or client calls detected -- this repository has no recognized "
                "web/API layer (FastAPI/Flask/Express/Django routes or fetch/axios clients)."
            )
        return result


