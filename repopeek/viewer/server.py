"""HTTP server for RepoPeek interactive code graph viewer.

Serves:
- Obsidian-style Canvas 2D graph viewer UI (HTML5 + D3 force physics at 60 FPS)
- REST APIs for graph, impact, context compiler, god nodes, cycles, and community clusters
"""

import json
from pathlib import Path
import threading
from typing import Any, Dict, Optional
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from repopeek.export.html import generate_html_content
from repopeek.graph.analysis import find_import_cycles, god_nodes
from repopeek.graph.clustering import detect_communities, generate_community_labels
from repopeek.query.engine import GraphQueryEngine
from repopeek.storage.json_store import load_lens


class GraphViewerHandler(BaseHTTPRequestHandler):
    """HTTP request handler serving the interactive graph viewer UI and JSON APIs."""

    engine: GraphQueryEngine
    storage_dir: Optional[Path] = None
    _cached_html: Optional[bytes] = None

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard HTTP server access logs to keep stdout clean."""
        return

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if path in ("/", "/index.html", "/graph.html"):
            self._serve_index()
        elif path == "/api/graph":
            lens = query_params.get("lens", ["all"])[0]
            self._serve_graph(lens)
        elif path == "/api/impact":
            target = query_params.get("target", [""])[0]
            depth = int(query_params.get("depth", [5])[0])
            self._serve_impact(target, depth)
        elif path == "/api/pack":
            target = query_params.get("target", [""])[0]
            self._serve_pack(target)
        elif path == "/api/context":
            task = query_params.get("task", [""])[0]
            budget = int(query_params.get("budget", [1500])[0])
            self._serve_context(task, budget)
        elif path == "/api/god-nodes":
            top_n = int(query_params.get("top_n", [10])[0])
            self._serve_god_nodes(top_n)
        elif path == "/api/cycles":
            self._serve_cycles()
        elif path == "/api/communities":
            self._serve_communities()
        elif path == "/api/routes":
            self._serve_routes()
        elif path == "/api/co-changes":
            target = query_params.get("target", [""])[0]
            self._serve_co_changes(target)
        else:
            self.send_error(404, "Not Found")

    def _send_json_response(self, data: Any) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_index(self) -> None:
        if GraphViewerHandler._cached_html is None:
            if hasattr(self.engine, "graph") and self.engine.graph:
                html_str = generate_html_content(self.engine.graph)
                GraphViewerHandler._cached_html = html_str.encode("utf-8")
            else:
                index_file = Path(__file__).parent / "index.html"
                if index_file.exists():
                    GraphViewerHandler._cached_html = index_file.read_bytes()

        if GraphViewerHandler._cached_html is None:
            self.send_error(404, "Graph visualization content not available")
            return

        content = GraphViewerHandler._cached_html
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content)

    def _serve_graph(self, lens_name: str) -> None:
        nodes_out = []
        edges_out = []

        if self.storage_dir and lens_name != "all":
            lens_file = self.storage_dir / "lenses" / f"{lens_name}.json"
            if lens_file.exists():
                try:
                    lens_graph = load_lens(self.storage_dir, lens_name)
                    for n in lens_graph.nodes.values():
                        dump = n.model_dump(exclude_none=True)
                        dump["label"] = n.display_label()
                        dump["language"] = n.id.split(":")[0] if ":" in n.id else ""
                        nodes_out.append(dump)
                    for e in lens_graph.edges:
                        edges_out.append({
                            "src": e.src,
                            "dst": e.dst,
                            "type": e.type.value if hasattr(e.type, "value") else str(e.type),
                        })
                except Exception:
                    pass

        if not nodes_out and hasattr(self.engine, "graph") and self.engine.graph:
            graph = self.engine.graph
            for n in graph.nodes.values():
                dump = n.model_dump(exclude_none=True)
                dump["label"] = n.display_label()
                dump["language"] = n.id.split(":")[0] if ":" in n.id else ""
                nodes_out.append(dump)
            for e in graph.edges:
                edges_out.append({
                    "src": e.src,
                    "dst": e.dst,
                    "type": e.type.value if hasattr(e.type, "value") else str(e.type),
                })

        self._send_json_response({"nodes": nodes_out, "edges": edges_out})

    def _serve_impact(self, target_query: str, max_depth: int) -> None:
        result = self.engine.impact(target_query, max_depth=max_depth)
        self._send_json_response(result)

    def _serve_pack(self, target_query: str) -> None:
        pack = self.engine.context_pack([target_query])
        payload = pack.to_markdown().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_context(self, task: str, budget: int) -> None:
        from repopeek.context import ContextCompiler
        compiler = ContextCompiler(self.engine)
        pkg = compiler.compile(task=task, token_budget=budget)
        self._send_json_response(pkg.to_dict())

    def _serve_god_nodes(self, top_n: int) -> None:
        nodes = god_nodes(self.engine.graph, top_n=top_n)
        self._send_json_response(nodes)

    def _serve_cycles(self) -> None:
        cycles = find_import_cycles(self.engine.graph)
        self._send_json_response({"cycles": cycles, "total": len(cycles)})

    def _serve_communities(self) -> None:
        communities = detect_communities(self.engine.graph)
        labels = generate_community_labels(self.engine.graph, communities)
        self._send_json_response({"communities": communities, "labels": labels})

    def _serve_routes(self) -> None:
        routes = self.engine.http_routes()
        self._send_json_response(routes)

    def _serve_co_changes(self, target: str) -> None:
        co = self.engine.co_changes(target)
        self._send_json_response(co)


def start_viewer(
    engine: GraphQueryEngine,
    storage_dir: Optional[Path] = None,
    port: int = 8765,
    open_browser: bool = True,
) -> ThreadingHTTPServer:
    """Start local threaded HTTP server serving the interactive graph viewer."""
    # Reset cached HTML across server restarts
    GraphViewerHandler._cached_html = None

    handler = type("ConfiguredGraphViewerHandler", (GraphViewerHandler,), {
        "engine": engine,
        "storage_dir": storage_dir,
    })

    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    url = f"http://127.0.0.1:{port}"
    print(f"RepoPeek Graph Viewer running at {url}")

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    return server
