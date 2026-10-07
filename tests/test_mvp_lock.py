"""Regression tests for MVP lock P0/P1 issues (RP-001 through RP-007)."""

from pathlib import Path

from repopeek.bridges.http import HttpBoundaryBridge, is_template_only_client_url
from repopeek.context.compiler import ContextCompiler
from repopeek.enrichment.summarizer import HierarchicalStoryGenerator
from repopeek.graph.blast_radius import compute_blast_radius, is_node_excluded
from repopeek.graph.builder import GraphBuilder
from repopeek.graph.identity import make_external_id
from repopeek.llm.fallback import DeterministicFallbackProvider
from repopeek.llm.factory import get_llm_provider
from repopeek.models.schema import CanonicalGraph, Confidence, Edge, EdgeType, NodeCard, NodeFacts, Span
from repopeek.parsers.python import PythonParser
from repopeek.parsers.typescript import TypeScriptParser
from repopeek.query.engine import GraphQueryEngine
from repopeek.retrieval.intent import extract_task_identifiers, resolve_task_to_symbols


def test_rp003_cross_language_next_does_not_collide(tmp_path: Path):
    """Python builtin next() and npm next must never share a graph identity."""
    (tmp_path / "chunk.py").write_text(
        "def walk(items):\n    return next(iter(items))\n",
        encoding="utf-8",
    )
    (tmp_path / "layout.tsx").write_text(
        'import Image from "next/image";\nexport default function Root() { return null; }\n',
        encoding="utf-8",
    )
    graph = GraphBuilder().build_from_directory(tmp_path)
    py_next = [e.dst for e in graph.edges if e.dst.endswith(":next") or e.dst.endswith(".next") or e.dst == "next"]
    ext_ids = [nid for nid in graph.nodes if nid.startswith("ext:")]
    assert "next" not in graph.nodes
    py_ext = [i for i in ext_ids if i.startswith("ext:py:") and i.endswith(":next")]
    ts_ext = [i for i in ext_ids if i.startswith("ext:ts:") and "next" in i]
    assert py_ext
    assert ts_ext
    assert set(py_ext).isdisjoint(set(ts_ext))

    walk_id = next(nid for nid in graph.nodes if nid.endswith("::walk"))
    report = compute_blast_radius(graph, walk_id, max_depth=5)
    total = len(report.direct) + len(report.indirect)
    assert total < 50
    assert len(report.traversed_edges) < 400


def test_rp001_django_urlpatterns_detected():
    source = '''
from django.urls import path, include, re_path
from .views import AuthView, health

urlpatterns = [
    path("api/v1/auth", AuthView.as_view()),
    path("api/v1/health", health),
    path("api/", include("apps.api.urls")),
    re_path(r"^legacy/$", health),
]
'''
    res = PythonParser().parse_source(source, rel_path="backend/urls.py")
    tags = []
    for n in res.nodes:
        tags.extend([r for r in n.facts.reads if r.startswith("ROUTE:")])
    joined = " ".join(tags)
    assert "api/v1/auth" in joined
    assert "api/v1/health" in joined


def test_rp002_http_wrapper_callers_tagged():
    source = '''
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(path, options);
  return res.json();
}

export async function fetchClients() {
  return request("/api/clients");
}

export async function fetchDocuments() {
  return request("/api/documents");
}
'''
    res = TypeScriptParser().parse_source(source, rel_path="frontend/src/lib/api.ts")
    by_name = {n.id.split("::")[-1]: n for n in res.nodes if n.kind == "function"}
    assert "fetchClients" in by_name
    client_reads = " ".join(by_name["fetchClients"].facts.reads)
    doc_reads = " ".join(by_name["fetchDocuments"].facts.reads)
    assert "/api/clients" in client_reads
    assert "/api/documents" in doc_reads


def test_rp004_schema_constraint_uses_kind_not_substring():
    n_fn = NodeCard(
        id="py:backend/tests/test_table_definition.py::test_table_definition_and_catalog",
        kind="function",
        span=Span(file="backend/tests/test_table_definition.py", start=1, end=10),
        facts=NodeFacts(),
        content_hash="a" * 16,
    )
    n_tbl = NodeCard(
        id="sql:db/schema.sql::table.invoices",
        kind="sql_table",
        span=Span(file="db/schema.sql", start=1, end=8),
        facts=NodeFacts(),
        content_hash="b" * 16,
    )
    from repopeek.models.schema import CanonicalGraph
    graph = CanonicalGraph(nodes={n_fn.id: n_fn, n_tbl.id: n_tbl}, edges=[])
    engine = GraphQueryEngine(graph=graph)
    compiler = ContextCompiler(engine)
    cs = compiler._extract_constraints([n_fn.id, n_tbl.id], [])
    joined = " ".join(cs.schema_constraints)
    assert n_tbl.id in joined
    assert n_fn.id not in joined


def test_rp007_must_not_edit_path_is_hard_excluded():
    task = "MUST NOT edit backend/services/neo4j/repositories/user.py when adding a serializer"
    intent = extract_task_identifiers(task)
    assert any("user.py" in x or "repositories" in x for x in intent.exclusions)
    assert "edit" not in [x.lower() for x in intent.exclusions]

    node_index = {
        "py:backend/services/neo4j/repositories/user.py::UserRepo": {
            "kind": "class",
            "file": "backend/services/neo4j/repositories/user.py",
            "sig": "class UserRepo",
            "story_text": "user repository",
        },
        "py:backend/api/serializers.py::UserSerializer": {
            "kind": "class",
            "file": "backend/api/serializers.py",
            "sig": "class UserSerializer",
            "story_text": "serializer",
        },
    }
    cands = resolve_task_to_symbols(task, node_index, limit=10)
    ids = [c.node_id for c in cands]
    assert all("user.py" not in i for i in ids)
    task = "MUST NOT edit backend/services/neo4j/repositories/user.py when adding a serializer"
    intent = extract_task_identifiers(task)
    assert any("user.py" in x or "repositories" in x for x in intent.exclusions)
    assert "edit" not in [x.lower() for x in intent.exclusions]

    node_index = {
        "py:backend/services/neo4j/repositories/user.py::UserRepo": {
            "kind": "class",
            "file": "backend/services/neo4j/repositories/user.py",
            "sig": "class UserRepo",
            "story_text": "user repository",
        },
        "py:backend/api/serializers.py::UserSerializer": {
            "kind": "class",
            "file": "backend/api/serializers.py",
            "sig": "class UserSerializer",
            "story_text": "serializer",
        },
    }
    cands = resolve_task_to_symbols(task, node_index, limit=10)
    ids = [c.node_id for c in cands]
    assert all("user.py" not in i for i in ids)


def test_rp006_application_intent_penalizes_docker_compose():
    task = "Change the API service endpoint handler for clients"
    intent = extract_task_identifiers(task)
    assert intent.task_kind == "application"
    node_index = {
        "yaml:docker-compose.yml::services.api.entrypoint": {
            "kind": "yaml_config",
            "file": "docker-compose.yml",
            "sig": "services.api.entrypoint",
            "story_text": "api service entrypoint",
        },
        "py:backend/api/views.py::ClientView": {
            "kind": "class",
            "file": "backend/api/views.py",
            "sig": "class ClientView",
            "story_text": "API clients endpoint",
        },
    }
    cands = resolve_task_to_symbols(task, node_index, limit=5)
    assert cands
    assert "ClientView" in cands[0].node_id


def test_rp005_compiler_does_not_dump_all_neighbors():
    from repopeek.models.schema import CanonicalGraph, Edge, EdgeType, Confidence

    nodes = {}
    edges = []
    entry = NodeCard(
        id="py:app/main.py::run",
        kind="function",
        span=Span(file="app/main.py", start=1, end=4),
        facts=NodeFacts(),
        content_hash="c" * 16,
    )
    nodes[entry.id] = entry
    for i in range(30):
        nid = f"py:app/util.py::helper_{i}"
        nodes[nid] = NodeCard(
            id=nid,
            kind="function",
            span=Span(file="app/util.py", start=i + 1, end=i + 1),
            facts=NodeFacts(),
            content_hash=str(i) * 16,
        )
        edges.append(Edge(src=entry.id, dst=nid, type=EdgeType.CALLS, confidence=Confidence.RESOLVED))
    graph = CanonicalGraph(nodes=nodes, edges=edges)
    engine = GraphQueryEngine(graph=graph)
    pkg = ContextCompiler(engine).compile("Change run helper in main", budget=1500, level=2)
    assert len(pkg.direct) + len(pkg.indirect) <= 25


def test_offline_llm_provider_is_usable_without_groq(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY_2", raising=False)
    monkeypatch.delenv("GROQ_API_KEY_3", raising=False)
    monkeypatch.setenv("REPOPEEK_OFFLINE", "1")
    provider = get_llm_provider()
    assert isinstance(provider, DeterministicFallbackProvider)


def test_http_bridge_links_django_and_wrapper(tmp_path: Path):
    (tmp_path / "urls.py").write_text(
        'from django.urls import path\nfrom views import list_clients\n'
        'urlpatterns = [path("api/clients", list_clients)]\n',
        encoding="utf-8",
    )
    (tmp_path / "views.py").write_text(
        "def list_clients(request):\n    return []\n",
        encoding="utf-8",
    )
    (tmp_path / "api.ts").write_text(
        "async function request(path: string) { return fetch(path); }\n"
        "export async function fetchClients() { return request('/api/clients'); }\n",
        encoding="utf-8",
    )
    graph = GraphBuilder().build_from_directory(tmp_path)
    bridge = HttpBoundaryBridge()
    routes = bridge.extract_server_routes(graph)
    calls = bridge.extract_client_calls(graph)
    assert any("clients" in r.raw_path for r in routes)
    assert any("clients" in c.raw_url for c in calls)
    edges = bridge.resolve_and_link(graph)
    assert any(e.type == EdgeType.INVOKES for e in edges)


def test_exclusion_matches_relative_and_bare_filename():
    assert is_node_excluded(
        "src/core/generate_synthetic_dataset.py",
        None,
        ["src/core/generate_synthetic_dataset.py"],
    )
    assert is_node_excluded(
        "py:src/core/generate_synthetic_dataset.py::<module>",
        None,
        ["generate_synthetic_dataset.py"],
    )
    assert is_node_excluded("app/api/users/views.py", None, ["app/api/users/views.py"])


def test_http_template_only_url_does_not_match_routes():
    assert is_template_only_client_url("${API_BASE_URL}${path}")
    assert is_template_only_client_url("/:param")
    assert not is_template_only_client_url("/api/v1/auth/login")


def test_neighbors_payload_is_capped():
    nodes = {}
    edges = []
    hub = NodeCard(id="py:a.py::hub", kind="function", span=Span(file="a.py", start=1, end=2), facts=NodeFacts(), content_hash="a" * 16)
    nodes[hub.id] = hub
    for i in range(80):
        nid = f"py:a.py::n{i}"
        nodes[nid] = NodeCard(id=nid, kind="function", span=Span(file="a.py", start=i + 3, end=i + 3), facts=NodeFacts(), content_hash=str(i).zfill(16))
        edges.append(Edge(src=hub.id, dst=nid, type=EdgeType.CALLS, confidence=Confidence.RESOLVED))
    engine = GraphQueryEngine(graph=CanonicalGraph(nodes=nodes, edges=edges))
    res = engine.neighbors(hub.id)
    assert len(res["outgoing"]) <= 30
    assert res.get("truncated") is True
    assert "src_card" not in res["outgoing"][0]


def test_external_symbol_is_trivial_for_llm():
    node = NodeCard(
        id=make_external_id("py", "stdlib", "re.sub"),
        kind="external_symbol",
        facts=NodeFacts(complexity=9, calls=4),
        content_hash="b" * 16,
    )
    assert HierarchicalStoryGenerator.is_trivial_node(node)


def test_compiler_strips_excluded_files():
    nodes = {
        "py:app/ok.py::run": NodeCard(
            id="py:app/ok.py::run",
            kind="function",
            span=Span(file="app/ok.py", start=1, end=4),
            facts=NodeFacts(),
            content_hash="c" * 16,
        ),
        "py:app/api/users/views.py::UserLoginView": NodeCard(
            id="py:app/api/users/views.py::UserLoginView",
            kind="class",
            span=Span(file="app/api/users/views.py", start=1, end=10),
            facts=NodeFacts(),
            content_hash="d" * 16,
        ),
    }
    graph = CanonicalGraph(nodes=nodes, edges=[])
    engine = GraphQueryEngine(graph=graph)
    pkg = ContextCompiler(engine).compile(
        "Fix login error in AuthContext.jsx. MUST NOT edit app/api/users/views.py",
        budget=1500,
        exclusions=["app/api/users/views.py"],
    )
    leaked = [f.replace("\\", "/") for f in pkg.affected_files if "views.py" in f.replace("\\", "/")]
    assert leaked == []


def test_nl_exclusion_or_paths_and_framework_prefix():
    intent = extract_task_identifiers(
        "Tighten login serializer. MUST NOT edit src/core/llm.py or generate_synthetic_dataset.py"
    )
    joined = " ".join(intent.exclusions)
    assert "llm.py" in joined
    assert "generate_synthetic_dataset.py" in joined
    intent2 = extract_task_identifiers(
        "Fix login error in AuthContext.jsx. Do not change Django UserLoginView"
    )
    assert any("UserLoginView" in x for x in intent2.exclusions)
    assert not any(x.lower() == "django" for x in intent2.exclusions)


def test_compiler_strips_login_view_from_nl_without_yaml():
    nodes = {
        "js:app/src/AuthContext.jsx::login": NodeCard(
            id="js:app/src/AuthContext.jsx::login",
            kind="function",
            span=Span(file="app/src/AuthContext.jsx", start=1, end=20),
            facts=NodeFacts(),
            content_hash="e" * 16,
        ),
        "py:app/api/users/views.py::UserLoginView": NodeCard(
            id="py:app/api/users/views.py::UserLoginView",
            kind="class",
            span=Span(file="app/api/users/views.py", start=1, end=10),
            facts=NodeFacts(),
            content_hash="f" * 16,
        ),
    }
    graph = CanonicalGraph(nodes=nodes, edges=[])
    pkg = ContextCompiler(GraphQueryEngine(graph=graph)).compile(
        "Fix login error in AuthContext.jsx. Do not change Django UserLoginView",
        budget=1500,
    )
    leaked = [f.replace("\\", "/") for f in pkg.affected_files if "views.py" in f.replace("\\", "/")]
    assert leaked == []


def test_loginpage_filename_stem_is_kept():
    nodes = {
        "js:app/src/pages/LoginPage.jsx::LoginPage": NodeCard(
            id="js:app/src/pages/LoginPage.jsx::LoginPage",
            kind="function",
            span=Span(file="app/src/pages/LoginPage.jsx", start=1, end=40),
            facts=NodeFacts(),
            content_hash="g" * 16,
        ),
        "py:app/api/users/views.py::UserLoginView": NodeCard(
            id="py:app/api/users/views.py::UserLoginView",
            kind="class",
            span=Span(file="app/api/users/views.py", start=1, end=20),
            facts=NodeFacts(),
            content_hash="h" * 16,
        ),
        "py:app/api/other/noise.py::helper": NodeCard(
            id="py:app/api/other/noise.py::helper",
            kind="function",
            span=Span(file="app/api/other/noise.py", start=1, end=4),
            facts=NodeFacts(),
            content_hash="i" * 16,
        ),
    }
    pkg = ContextCompiler(GraphQueryEngine(graph=CanonicalGraph(nodes=nodes, edges=[]))).compile(
        "In UserLoginView.post where remember_me sets REMEMBER_ME_DAYS, align with frontend LoginPage.jsx",
        budget=1500,
    )
    files = [f.replace("\\", "/") for f in pkg.affected_files]
    assert any("LoginPage.jsx" in f for f in files)


def test_sql_command_recovers_table_not_extension(tmp_path: Path):
    sql = (
        'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";\n'
        "CREATE TABLE widgets (id uuid PRIMARY KEY);\n"
        "CREATE OR REPLACE FUNCTION fix_timezone_setting() RETURNS void AS $$ BEGIN END; $$ LANGUAGE plpgsql;\n"
    )
    (tmp_path / "init.sql").write_text(sql, encoding="utf-8")
    graph = GraphBuilder(sql_dialect="postgres").build_from_directory(tmp_path)
    assert any("widgets" in nid for nid in graph.nodes)


def test_identifier_http_urls_do_not_link():
    assert is_template_only_client_url("downloadUrl")
    assert is_template_only_client_url("wrapper")

