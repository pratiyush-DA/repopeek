"""Tests for Cross-Language HTTP Boundary Bridge."""

import pytest
from pathlib import Path

from repopeek.bridges.http import (
    HttpBoundaryBridge,
    normalize_route_path,
    paths_match,
)
from repopeek.graph.blast_radius import compute_blast_radius
from repopeek.graph.builder import GraphBuilder
from repopeek.graph.lenses import get_bridges_lens
from repopeek.models.schema import (
    CanonicalGraph,
    Confidence,
    Edge,
    EdgeType,
    NodeCard,
    NodeFacts,
    NodeStory,
    Span,
)
from repopeek.parsers.python import PythonParser
from repopeek.parsers.typescript import TypeScriptParser
from repopeek.query.engine import GraphQueryEngine


def test_normalize_route_path():
    """Verify URL paths and wildcard parameter templates normalize to :param."""
    assert normalize_route_path("/api/users/{user_id}") == "/api/users/:param"
    assert normalize_route_path("/api/users/:userId") == "/api/users/:param"
    assert normalize_route_path("/api/users/${id}") == "/api/users/:param"
    assert normalize_route_path("/api/users/<int:user_id>") == "/api/users/:param"
    assert normalize_route_path("/api/users/98765") == "/api/users/:param"
    assert normalize_route_path("http://localhost:8000/api/users") == "/api/users"
    assert normalize_route_path("${API_BASE}/auth/login") == "/auth/login"
    assert normalize_route_path("") == "/"
    assert normalize_route_path("/users") == "/users"


def test_paths_match():
    """Verify path matching with wildcards and relative prefixes."""
    assert paths_match("/api/users/:param", "/api/users/:param")
    assert paths_match("/api/users/:param", "/api/users/123")
    assert paths_match("/users/:param", "/api/users/:param")
    assert not paths_match("/api/orders", "/api/users")
    assert not paths_match("", "/api/users")


def test_cross_language_parsing_and_resolution(tmp_path: Path):
    """Test fullstack Python backend + TypeScript frontend parsing and linking."""
    backend_py = """\"\"\"User management API.\"\"\"
from fastapi import FastAPI, APIRouter

app = FastAPI()
router = APIRouter()

@app.get("/api/v1/users/{user_id}")
def get_user_by_id(user_id: str):
    return {"id": user_id, "name": "Alice"}

@app.post("/api/v1/users")
def create_user(payload: dict):
    return {"status": "created"}
"""
    frontend_ts = """/** User client service. */
import axios from 'axios';

export async function fetchUserProfile(userId: string) {
    const response = await fetch(`/api/v1/users/${userId}`);
    return response.json();
}

export const submitNewUser = async (data: any) => {
    return await axios.post('/api/v1/users', data);
};

export async function getHealth() {
    return await axios.get('/health');
}
"""
    py_file = tmp_path / "backend" / "routes.py"
    py_file.parent.mkdir(parents=True)
    py_file.write_text(backend_py, encoding="utf-8")

    ts_file = tmp_path / "frontend" / "client.ts"
    ts_file.parent.mkdir(parents=True)
    ts_file.write_text(frontend_ts, encoding="utf-8")

    py_parser = PythonParser()
    ts_parser = TypeScriptParser()

    py_res = py_parser.parse_file(py_file, repo_root=tmp_path)
    ts_res = ts_parser.parse_file(ts_file, repo_root=tmp_path)

    builder = GraphBuilder()
    graph = builder.build([py_res, ts_res])

    # Verify INVOKES edges exist between frontend and backend
    invokes_edges = [e for e in graph.edges if e.type == EdgeType.INVOKES]
    assert len(invokes_edges) >= 2

    # Check fetchUserProfile -> get_user_by_id
    get_edge = next(
        (e for e in invokes_edges if "fetchUserProfile" in e.src and "get_user_by_id" in e.dst),
        None,
    )
    assert get_edge is not None
    assert get_edge.confidence == Confidence.RESOLVED
    assert "http_boundary" in get_edge.evidence.how_derived

    # Check submitNewUser -> create_user
    post_edge = next(
        (e for e in invokes_edges if "submitNewUser" in e.src and "create_user" in e.dst),
        None,
    )
    assert post_edge is not None
    assert post_edge.confidence == Confidence.RESOLVED

    # Verify Bridges Lens includes cross-language HTTP edges
    bridges_graph = get_bridges_lens(graph)
    assert any(e.type == EdgeType.INVOKES for e in bridges_graph.edges)

    # Verify Upstream Blast Radius from backend to frontend
    server_node_id = get_edge.dst
    blast_upstream = compute_blast_radius(graph, target_id=server_node_id, direction="upstream")
    assert any(item.node_id == get_edge.src for item in blast_upstream.direct)

    # Verify GraphQueryEngine http_routes output
    engine = GraphQueryEngine(graph=graph)
    routes_summary = engine.http_routes()
    assert routes_summary["total_routes"] >= 2
    assert routes_summary["total_calls"] >= 3
    assert routes_summary["total_links"] >= 2


def test_flask_methods_and_method_mismatch(tmp_path: Path):
    """Test Flask @bp.route with explicit methods and verify method mismatch avoids false positive."""
    flask_py = """\"\"\"Flask blueprint.\"\"\"
from flask import Blueprint

bp = Blueprint('orders', __name__)

@bp.route('/orders', methods=['POST'])
def create_order():
    return {'id': 1}
"""
    client_ts = """/** Client calls. */
import axios from 'axios';

export async function placeOrder() {
    return await axios.post('/orders', { item: 'book' });
}

export async function listOrders() {
    return await axios.get('/orders');
}
"""
    py_file = tmp_path / "orders.py"
    py_file.write_text(flask_py, encoding="utf-8")
    ts_file = tmp_path / "client.ts"
    ts_file.write_text(client_ts, encoding="utf-8")

    py_res = PythonParser().parse_file(py_file, repo_root=tmp_path)
    ts_res = TypeScriptParser().parse_file(ts_file, repo_root=tmp_path)

    graph = GraphBuilder().build([py_res, ts_res])
    invokes = [e for e in graph.edges if e.type == EdgeType.INVOKES]

    # POST should link to create_order
    assert any("placeOrder" in e.src and "create_order" in e.dst for e in invokes)

    # GET should NOT link to POST-only create_order
    assert not any("listOrders" in e.src and "create_order" in e.dst for e in invokes)


def test_express_server_route_linking(tmp_path: Path):
    """Test Node.js / Express backend route linked to frontend client."""
    express_ts = """/** Express server. */
import express from 'express';
const app = express();

export function registerRoutes() {
    app.get('/api/healthz', (req, res) => {
        res.json({ status: 'ok' });
    });
}
"""
    client_ts = """/** Frontend monitor. */
export async function checkServerHealth() {
    return await fetch('/api/healthz');
}
"""
    server_file = tmp_path / "server.ts"
    server_file.write_text(express_ts, encoding="utf-8")
    client_file = tmp_path / "monitor.ts"
    client_file.write_text(client_ts, encoding="utf-8")

    server_res = TypeScriptParser().parse_file(server_file, repo_root=tmp_path)
    client_res = TypeScriptParser().parse_file(client_file, repo_root=tmp_path)

    graph = GraphBuilder().build([server_res, client_res])
    invokes = [e for e in graph.edges if e.type == EdgeType.INVOKES]
    assert len(invokes) >= 1
    assert any("checkServerHealth" in e.src and "registerRoutes" in e.dst for e in invokes)


def test_python_route_decorator_edge_cases(tmp_path: Path):
    """Test Python parser route decorators with custom attributes, bare names, and complex funcs."""
    source_py = """\"\"\"Route decorator edge cases.\"\"\"
def get(path):
    def dec(fn): return fn
    return dec

def route(path):
    def dec(fn): return fn
    return dec

class Api:
    def custom_endpoint(self, path):
        def dec(fn): return fn
        return dec

api = Api()

@get('/bare/get')
def fn_bare_get():
    pass

@route('/bare/route')
def fn_bare_route():
    pass

@api.custom_endpoint('/custom/endpoint')
def fn_custom():
    pass
"""
    f = tmp_path / "edge_routes.py"
    f.write_text(source_py, encoding="utf-8")

    res = PythonParser().parse_file(f, repo_root=tmp_path)
    nodes_by_name = {n.id.split(":")[-1]: n for n in res.nodes}

    assert "ROUTE:GET:/bare/get" in nodes_by_name["fn_bare_get"].facts.reads
    assert "ROUTE:ANY:/bare/route" in nodes_by_name["fn_bare_route"].facts.reads
    assert "ROUTE:CUSTOM_ENDPOINT:/custom/endpoint" in nodes_by_name["fn_custom"].facts.reads


