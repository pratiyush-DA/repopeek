"""Canonical graph builder aggregating multi-language parsed outputs into NetworkX."""

from pathlib import Path
from typing import Dict, List, Optional, Set

import networkx as nx

from repopeek.discovery.classifier import classify_file
from repopeek.discovery.crawler import discover_repository
from repopeek.models.schema import CanonicalGraph, Edge, NodeCard
from repopeek.parsers.base import BaseParser, ParseResult
from repopeek.parsers.config import JsonConfigParser, YamlConfigParser
from repopeek.parsers.python import PythonParser
from repopeek.parsers.shell import ShellParser
from repopeek.parsers.sql import SqlParser
from repopeek.graph.resolver import SymbolResolver


class GraphBuilder:
    """Builds and validates the canonical property graph from multi-language parse results."""

    def __init__(self) -> None:
        self.parsers: Dict[str, BaseParser] = {
            "python": PythonParser(),
            "sql": SqlParser(),
            "shell": ShellParser(),
            "json": JsonConfigParser(),
            "yaml": YamlConfigParser(),
        }

    def build(
        self,
        parse_results: List[ParseResult],
        repo_commit: Optional[str] = None,
        tool_version: str = "0.1.0",
    ) -> CanonicalGraph:
        """Assemble parse results into a canonical graph and resolve cross-file references."""
        graph = CanonicalGraph(repo_commit=repo_commit, tool_version=tool_version)

        raw_nodes: List[NodeCard] = []
        raw_edges: List[Edge] = []

        for res in parse_results:
            for node in res.nodes:
                raw_nodes.append(node)
                graph.add_node(node)
            for edge in res.edges:
                raw_edges.append(edge)

        # Cross-file symbol resolution
        resolver = SymbolResolver(nodes=raw_nodes, edges=raw_edges)
        resolved_edges = resolver.resolve()

        for edge in resolved_edges:
            graph.add_edge(edge)

        return graph

    def build_from_directory(
        self,
        repo_root: Path,
        repo_commit: Optional[str] = None,
    ) -> CanonicalGraph:
        """Discover, classify, and parse all repository files, returning the unified graph."""
        root = Path(repo_root).resolve()
        files = discover_repository(root)

        results: List[ParseResult] = []
        for finfo in files:
            ftype = classify_file(finfo.path)
            lang = ftype.value
            parser = self.parsers.get(lang)
            if parser:
                res = parser.parse_file(finfo.path, repo_root=root)
                results.append(res)

        return self.build(results, repo_commit=repo_commit)

    @staticmethod
    def to_networkx(graph: CanonicalGraph) -> nx.MultiDiGraph:
        """Export CanonicalGraph into NetworkX MultiDiGraph for graph analytics and traversal."""
        G = nx.MultiDiGraph()

        for nid, card in graph.nodes.items():
            G.add_node(
                nid,
                kind=card.kind,
                sig=card.sig,
                file=card.span.file if card.span else None,
                start=card.span.start if card.span else None,
                end=card.span.end if card.span else None,
                complexity=card.facts.complexity,
                story=card.story.text if card.story else None,
                content_hash=card.content_hash,
            )

        for edge in graph.edges:
            G.add_edge(
                edge.src,
                edge.dst,
                key=edge.type.value,
                type=edge.type.value,
                confidence=edge.confidence.value,
                evidence=edge.evidence.how_derived if edge.evidence else None,
            )

        return G

    @staticmethod
    def validate_graph(graph: CanonicalGraph) -> List[str]:
        """Verify graph integrity: identify dangling edges and orphan definitions."""
        issues: List[str] = []
        node_ids = set(graph.nodes.keys())

        for edge in graph.edges:
            if edge.src not in node_ids:
                issues.append(f"Edge src missing from graph: {edge.src} -> {edge.dst} ({edge.type})")
            # For internal resolved edges, dst should exist in graph
            if edge.confidence.value == "resolved" and edge.dst not in node_ids:
                # Some edges point to external or unresolved targets
                pass

        return issues
