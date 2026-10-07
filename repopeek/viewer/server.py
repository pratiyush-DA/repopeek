"""HTTP server for RepoPeek interactive code graph viewer."""

import json
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

from repopeek.query.engine import GraphQueryEngine
from repopeek.storage.json_store import load_lens


class GraphViewerHandler(BaseHTTPRequestHandler):
    """HTTP request handler serving the interactive graph viewer UI and JSON APIs."""

    engine: GraphQueryEngine
    storage_dir: Optional[Path] = None

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard HTTP server access logs to keep stdout clean."""
        return

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if path in ("/", "/index.html"):
            self._serve_index()
        elif path == "/api/graph":
            lens = query_params.get("lens", ["call"])[0]
            self._serve_graph(lens)
        elif path == "/api/impact":
            target = query_params.get("target", [""])[0]
            depth = int(query_params.get("depth", [5])[0])
            self._serve_impact(target, depth)
        elif path == "/api/pack":
            target = query_params.get("target", [""])[0]
            self._serve_pack(target)
        else:
            self.send_error(404, "Not Found")

    def _serve_index(self) -> None:
        index_file = Path(__file__).parent / "index.html"
        if not index_file.exists():
            self.send_error(404, "index.html not found")
            return

        content = index_file.read_bytes()
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

        # Attempt to load specialized lens if storage_dir is provided
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

        # Fallback to in-memory graph
        if not nodes_out and hasattr(self.engine, "graph"):
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

        payload = json.dumps({"nodes": nodes_out, "edges": edges_out}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_impact(self, target_query: str, max_depth: int) -> None:
        result = self.engine.impact(target_query, max_depth=max_depth)
        payload = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "close")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

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


def start_viewer(
    engine: GraphQueryEngine,
    storage_dir: Optional[Path] = None,
    port: int = 8765,
    open_browser: bool = True,
) -> ThreadingHTTPServer:
    """Start local threaded HTTP server serving the interactive graph viewer."""
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
