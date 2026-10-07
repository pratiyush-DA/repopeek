"""Cross-Language HTTP Boundary Bridge for RepoPeek.

Bridges TypeScript/JavaScript client API calls (fetch, axios, apiClient)
to backend route handlers (FastAPI, Flask, Express, Starlette) with
wildcard path parameter normalization (:param, {param}, <param>).
"""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from repopeek.models.schema import CanonicalGraph, Confidence, Edge, EdgeType, Evidence, NodeCard


# ---------------------------------------------------------------------------
# Path Parameter & URL Normalization
# ---------------------------------------------------------------------------

PARAM_TOKEN_RE = re.compile(
    r"^(:[a-zA-Z0-9_$]+|\{[a-zA-Z0-9_$]+\}|<[a-zA-Z0-9_$:.]+>|\$\{[a-zA-Z0-9_$.]+\}|\d+|[0-9a-fA-F-]{36})$"
)

HTTP_CLIENT_CALL_RE = re.compile(
    r"\b(?:fetch\s*\(\s*['\"`]?([^'\"`,\)\s]+)['\"`]?(?:\s*,\s*\{[^}]*method\s*:\s*['\"]([a-zA-Z]+)['\"])?"
    r"|(?:axios|apiClient|requests|httpx)\.(get|post|put|delete|patch)\s*\(\s*['\"`]?([^'\"`,\)\s]+)['\"`]?"
    r"|(?:axios|apiClient)\s*\(\s*\{[^}]*url\s*:\s*['\"`]?([^'\"`,\s]+)['\"`]?[^}]*method\s*:\s*['\"]([a-zA-Z]+)['\"])",
    re.IGNORECASE,
)

ROUTE_DECORATOR_RE = re.compile(
    r"@(?:(?:[a-zA-Z0-9_]+\.)?(get|post|put|delete|patch|options|head|route))\s*\(\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)

FLASK_ROUTE_RE = re.compile(
    r"@(?:[a-zA-Z0-9_]+)\.route\s*\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?",
    re.IGNORECASE,
)

EXPRESS_ROUTE_RE = re.compile(
    r"\b(?:app|router|server)\.(get|post|put|delete|patch|all)\s*\(\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)


def normalize_route_path(path: str) -> str:
    """Normalize any endpoint URL path into a canonical template with :param wildcards.

    Examples:
        /api/users/{user_id}      -> /api/users/:param
        /api/users/:userId        -> /api/users/:param
        /api/users/${id}          -> /api/users/:param
        /api/users/<int:user_id>  -> /api/users/:param
        /api/users/12345          -> /api/users/:param
        ${this.apiUrl}/users      -> /users
    """
    if not path or not path.strip():
        return "/"

    # Strip query parameters and fragment
    cleaned = path.split("?")[0].split("#")[0].strip()

    # Strip domain/protocol if absolute URL
    if "://" in cleaned:
        cleaned = cleaned.split("://", 1)[-1]
        if "/" in cleaned:
            cleaned = "/" + cleaned.split("/", 1)[-1]
        else:
            cleaned = "/"

    # Strip a leading template variable like ${API_URL} or $apiUrl, preserving any literal
    # path that follows even when it is concatenated without a slash
    # (e.g. ${API_BASE_URL}auth/login -> /auth/login, not /login).
    if cleaned.startswith("${"):
        cleaned = re.sub(r"^\$\{[^}]*\}", "", cleaned)
    elif cleaned.startswith("$") and "/" in cleaned:
        cleaned = cleaned.split("/", 1)[-1]
    if cleaned and not cleaned.startswith("/"):
        cleaned = "/" + cleaned

    raw_segments = [s.strip() for s in cleaned.strip("/").split("/") if s.strip()]
    norm_segments = []

    for seg in raw_segments:
        if PARAM_TOKEN_RE.match(seg):
            norm_segments.append(":param")
        elif "{" in seg and "}" in seg:
            norm_segments.append(":param")
        elif "${" in seg:
            norm_segments.append(":param")
        elif "<" in seg and ">" in seg:
            norm_segments.append(":param")
        else:
            norm_segments.append(seg.lower())

    return "/" + "/".join(norm_segments)


def is_template_only_client_url(raw_url: str) -> bool:
    """True when the client URL has no literal path segment and cannot uniquely match a route."""
    text = (raw_url or "").strip()
    if not text:
        return True
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text):
        return True
    if "${" in text and "path" in text.lower():
        return True
    norm = normalize_route_path(text)
    segs = [p for p in norm.strip("/").split("/") if p]
    return (not segs) or all(p == ":param" for p in segs)


def _literal_segments(norm_path: str) -> List[str]:
    return [s for s in norm_path.strip("/").split("/") if s and s != ":param"]


def paths_match(client_norm: str, server_norm: str) -> bool:
    """Return True if normalized client request path matches server endpoint template."""
    if is_template_only_client_url(client_norm):
        return False
    if client_norm == server_norm:
        return True

    c_segs = [s for s in client_norm.strip("/").split("/") if s]
    s_segs = [s for s in server_norm.strip("/").split("/") if s]

    if not c_segs or not s_segs:
        return False

    def _compatible(a: List[str], b: List[str]) -> bool:
        if not a or not b:
            return False
        if not all(c == s or c == ":param" or s == ":param" for c, s in zip(a, b)):
            return False
        shared = set(_literal_segments("/" + "/".join(a))) & set(_literal_segments("/" + "/".join(b)))
        return len(shared) >= 1

    if len(c_segs) == len(s_segs):
        return _compatible(c_segs, s_segs)

    min_len = min(len(c_segs), len(s_segs))
    if min_len >= 2:
        return _compatible(c_segs[-min_len:], s_segs[-min_len:])
    return False


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

@dataclass
class RouteEndpoint:
    """Extracted server route endpoint."""
    node_id: str
    method: str
    raw_path: str
    norm_path: str
    file: str
    line: int


@dataclass
class HttpClientCall:
    """Extracted client HTTP call."""
    caller_node_id: str
    method: Optional[str]
    raw_url: str
    norm_path: str
    file: str
    line: int


# ---------------------------------------------------------------------------
# HttpBoundaryBridge
# ---------------------------------------------------------------------------

class HttpBoundaryBridge:
    """Discovers, normalizes, and connects client HTTP requests to backend routes."""

    def extract_server_routes(self, graph: CanonicalGraph) -> List[RouteEndpoint]:
        """Discover server route endpoints across Python and Node.js route handlers."""
        routes: List[RouteEndpoint] = []

        for nid, node in graph.nodes.items():
            if node.kind not in ("function", "method", "class", "file", "module"):
                continue

            file_path = node.span.file if node.span else ""
            line_no = node.span.start if node.span else 1

            # 1. Check facts.reads for ROUTE: tags
            for r in node.facts.reads:
                if r.startswith("ROUTE:"):
                    parts = r.split(":", 2)
                    if len(parts) == 3:
                        m_str, path_str = parts[1].upper(), parts[2]
                        routes.append(
                            RouteEndpoint(
                                node_id=nid,
                                method=m_str,
                                raw_path=path_str,
                                norm_path=normalize_route_path(path_str),
                                file=file_path,
                                line=line_no,
                            )
                        )

            # 2. Check snippet or sig for route decorators
            search_text = f"{node.sig or ''}\n{node.snippet or ''}"
            for m in ROUTE_DECORATOR_RE.finditer(search_text):
                m_str = m.group(1).upper()
                if m_str == "ROUTE":
                    m_str = "ANY"
                path_str = m.group(2)
                norm_p = normalize_route_path(path_str)
                if not any(r.node_id == nid and r.norm_path == norm_p for r in routes):
                    routes.append(
                        RouteEndpoint(
                            node_id=nid,
                            method=m_str,
                            raw_path=path_str,
                            norm_path=norm_p,
                            file=file_path,
                            line=line_no,
                        )
                    )

            # 3. Check Flask style @app.route with methods=[...]
            for m in FLASK_ROUTE_RE.finditer(search_text):
                path_str = m.group(1)
                methods_str = m.group(2)
                norm_p = normalize_route_path(path_str)
                if methods_str:
                    m_list = [x.strip(" '\"").upper() for x in methods_str.split(",") if x.strip(" '\"")]
                else:
                    m_list = ["GET"]
                for m_str in m_list:
                    if not any(r.node_id == nid and r.norm_path == norm_p and (r.method == m_str or m_str == "ANY") for r in routes):
                        routes.append(
                            RouteEndpoint(
                                node_id=nid,
                                method=m_str,
                                raw_path=path_str,
                                norm_path=norm_p,
                                file=file_path,
                                line=line_no,
                            )
                        )

            # 4. Check Express route handlers
            for m in EXPRESS_ROUTE_RE.finditer(search_text):
                m_str = m.group(1).upper()
                if m_str == "ALL":
                    m_str = "ANY"
                path_str = m.group(2)
                norm_p = normalize_route_path(path_str)
                if not any(r.node_id == nid and r.norm_path == norm_p for r in routes):
                    routes.append(
                        RouteEndpoint(
                            node_id=nid,
                            method=m_str,
                            raw_path=path_str,
                            norm_path=norm_p,
                            file=file_path,
                            line=line_no,
                        )
                    )

        return routes

    def extract_client_calls(self, graph: CanonicalGraph) -> List[HttpClientCall]:
        """Discover client HTTP calls (fetch, axios, apiClient) across graph nodes."""
        calls: List[HttpClientCall] = []

        for nid, node in graph.nodes.items():
            file_path = node.span.file if node.span else ""
            line_no = node.span.start if node.span else 1

            # 1. Check facts.reads for HTTP: tags
            for r in node.facts.reads:
                if r.startswith("HTTP:"):
                    raw_val = r[5:]
                    method = None
                    if ":" in raw_val:
                        parts = raw_val.split(":", 1)
                        if parts[0].upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                            method = parts[0].upper()
                            raw_val = parts[1]
                    if is_template_only_client_url(raw_val):
                        continue
                    calls.append(
                        HttpClientCall(
                            caller_node_id=nid,
                            method=method,
                            raw_url=raw_val,
                            norm_path=normalize_route_path(raw_val),
                            file=file_path,
                            line=line_no,
                        )
                    )

            # 2. Check snippet for fetch / axios calls
            if node.snippet:
                for m in HTTP_CLIENT_CALL_RE.finditer(node.snippet):
                    # fetch pattern: group(1), group(2)
                    # axios method: group(3), group(4)
                    # axios config: group(5), group(6)
                    raw_url = m.group(1) or m.group(4) or m.group(5)
                    method = m.group(2) or m.group(3) or m.group(6)
                    if method:
                        method = method.upper()

                    if raw_url:
                        if is_template_only_client_url(raw_url):
                            continue
                        norm_p = normalize_route_path(raw_url)
                        if not any(c.caller_node_id == nid and c.norm_path == norm_p for c in calls):
                            calls.append(
                                HttpClientCall(
                                    caller_node_id=nid,
                                    method=method,
                                    raw_url=raw_url,
                                    norm_path=norm_p,
                                    file=file_path,
                                    line=line_no,
                                )
                            )

        return calls

    def resolve_and_link(self, graph: CanonicalGraph) -> List[Edge]:
        """Match client calls with server endpoints and return typed INVOKES edges."""
        server_routes = self.extract_server_routes(graph)
        client_calls = self.extract_client_calls(graph)

        edges: List[Edge] = []
        seen = set()

        for client in client_calls:
            candidates: List[Tuple[int, RouteEndpoint]] = []
            for server in server_routes:
                if not paths_match(client.norm_path, server.norm_path):
                    continue
                if client.method and server.method != "ANY":
                    if client.method.upper() != server.method.upper():
                        continue
                n_lit = len(_literal_segments(server.norm_path))
                candidates.append((n_lit, server))
            if not candidates:
                continue
            best = max(n for n, _ in candidates)
            for n_lit, server in candidates:
                if n_lit != best:
                    continue
                edge_key = (client.caller_node_id, server.node_id)
                if edge_key not in seen and client.caller_node_id != server.node_id:
                    seen.add(edge_key)
                    m_label = client.method or server.method or "HTTP"
                    edges.append(
                        Edge(
                            src=client.caller_node_id,
                            dst=server.node_id,
                            type=EdgeType.INVOKES,
                            confidence=Confidence.RESOLVED,
                            evidence=Evidence(
                                file=client.file,
                                start_line=client.line,
                                end_line=client.line,
                                how_derived=f"http_boundary({m_label} {client.raw_url} -> {server.method} {server.raw_path})",
                            ),
                        )
                    )

        return edges
