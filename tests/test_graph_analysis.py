"""Tests for graph topological analysis engine: god nodes, cycles, surprising edges, diff."""

import pytest
from repopeek.graph.analysis import (
    find_import_cycles,
    god_nodes,
    graph_diff,
    suggest_questions,
    surprising_connections,
)
from repopeek.models.schema import (
    CanonicalGraph,
    Confidence,
    Edge,
    EdgeType,
    Evidence,
    NodeCard,
    NodeFacts,
    Span,
)


def _build_test_graph() -> CanonicalGraph:
    graph = CanonicalGraph()

    # Create nodes
    hub = NodeCard(
        id="py:core/engine.py::Engine",
        kind="class",
        sig="Engine",
        span=Span(file="core/engine.py", start=10, end=100),
        facts=NodeFacts(complexity=8),
        content_hash="hash_engine",
    )
    worker = NodeCard(
        id="py:core/worker.py::Worker",
        kind="class",
        sig="Worker",
        span=Span(file="core/worker.py", start=5, end=50),
        facts=NodeFacts(complexity=4),
        content_hash="hash_worker",
    )
    api = NodeCard(
        id="py:api/routes.py::get_status",
        kind="function",
        sig="get_status()",
        span=Span(file="api/routes.py", start=1, end=20),
        facts=NodeFacts(complexity=2),
        content_hash="hash_api",
    )
    client = NodeCard(
        id="ts:client/src/api.ts::fetchStatus",
        kind="function",
        sig="fetchStatus()",
        span=Span(file="client/src/api.ts", start=15, end=35),
        facts=NodeFacts(complexity=1),
        content_hash="hash_client",
    )
    noise_node = NodeCard(
        id="py:core/types.py::str",
        kind="class",
        sig="str",
        span=Span(file="core/types.py", start=1, end=2),
        facts=NodeFacts(),
        content_hash="hash_str",
    )

    for n in [hub, worker, api, client, noise_node]:
        graph.add_node(n)

    # Edges
    # Worker -> Engine
    graph.add_edge(Edge(src=worker.id, dst=hub.id, type=EdgeType.CALLS, confidence=Confidence.RESOLVED))
    # API -> Engine
    graph.add_edge(Edge(src=api.id, dst=hub.id, type=EdgeType.CALLS, confidence=Confidence.RESOLVED))
    # Client -> API (cross-language)
    graph.add_edge(Edge(src=client.id, dst=api.id, type=EdgeType.INVOKES, confidence=Confidence.AMBIGUOUS))
    # Engine -> noise
    graph.add_edge(Edge(src=hub.id, dst=noise_node.id, type=EdgeType.READS, confidence=Confidence.RESOLVED))

    return graph


def test_god_nodes_ranking_and_noise_exclusion():
    graph = _build_test_graph()
    gods = god_nodes(graph, top_n=5)
    assert len(gods) > 0
    # Engine should be the top god node
    assert gods[0]["id"] == "py:core/engine.py::Engine"
    assert gods[0]["degree"] >= 3
    # Primitive 'str' node must be excluded from god nodes
    assert not any(g["label"] == "str" for g in gods)


def test_surprising_connections_detection():
    graph = _build_test_graph()
    communities = {
        0: ["py:core/engine.py::Engine", "py:core/worker.py::Worker"],
        1: ["py:api/routes.py::get_status"],
        2: ["ts:client/src/api.ts::fetchStatus"],
    }
    surprises = surprising_connections(graph, communities=communities, top_n=5)
    assert len(surprises) > 0
    # The client -> api edge crosses language and community and directory boundaries
    top_surprise = surprises[0]
    assert "ts:client/src/api.ts::fetchStatus" in top_surprise["src"]
    assert "py:api/routes.py::get_status" in top_surprise["dst"]
    assert top_surprise["score"] > 5


def test_find_import_cycles():
    graph = CanonicalGraph()
    # Create cycle: a.py -> b.py -> c.py -> a.py
    n_a = NodeCard(id="py:a.py::A", kind="class", sig="A", span=Span(file="a.py", start=1, end=5), content_hash="h1")
    n_b = NodeCard(id="py:b.py::B", kind="class", sig="B", span=Span(file="b.py", start=1, end=5), content_hash="h2")
    n_c = NodeCard(id="py:c.py::C", kind="class", sig="C", span=Span(file="c.py", start=1, end=5), content_hash="h3")
    for n in [n_a, n_b, n_c]:
        graph.add_node(n)

    graph.add_edge(Edge(src=n_a.id, dst=n_b.id, type=EdgeType.IMPORTS))
    graph.add_edge(Edge(src=n_b.id, dst=n_c.id, type=EdgeType.IMPORTS))
    graph.add_edge(Edge(src=n_c.id, dst=n_a.id, type=EdgeType.IMPORTS))

    cycles = find_import_cycles(graph)
    assert len(cycles) > 0
    flat_cycle = [p for cycle in cycles for p in cycle]
    assert "a.py" in flat_cycle
    assert "b.py" in flat_cycle
    assert "c.py" in flat_cycle


def test_calls_and_inheritance_do_not_produce_import_cycles():
    graph = CanonicalGraph()
    # a.py imports b.py; b.py calls a.py (e.g. interface/implementation pattern)
    n_a = NodeCard(id="py:a.py::Interface", kind="class", sig="Interface", span=Span(file="a.py", start=1, end=10), content_hash="h1")
    n_b = NodeCard(id="py:b.py::Impl", kind="class", sig="Impl", span=Span(file="b.py", start=1, end=20), content_hash="h2")
    graph.add_node(n_a)
    graph.add_node(n_b)

    # b.py imports a.py
    graph.add_edge(Edge(src=n_b.id, dst=n_a.id, type=EdgeType.IMPORTS))
    # a.py calls b.py method (dynamic or abstract dispatch)
    graph.add_edge(Edge(src=n_a.id, dst=n_b.id, type=EdgeType.CALLS))

    cycles = find_import_cycles(graph)
    # CALLS must NOT be counted as an import cycle
    assert len(cycles) == 0


def test_suggest_questions():
    graph = _build_test_graph()
    questions = suggest_questions(graph, top_n=5)
    assert len(questions) > 0
    assert any("Engine" in q for q in questions)


def test_external_and_unresolved_nodes_excluded_from_god_nodes():
    graph = CanonicalGraph()
    # Add real class
    real_cls = NodeCard(
        id="py:core/app.py::Application",
        kind="class",
        sig="Application",
        span=Span(file="core/app.py", start=1, end=50),
        facts=NodeFacts(complexity=5),
        content_hash="h_app",
    )
    # Add external builtin and unresolved nodes with high degree
    ext_builtin = NodeCard(
        id="ext:py:builtin:len",
        kind="external_symbol",
        sig="len",
        span=None,
        content_hash="h_len",
    )
    unresolved_node = NodeCard(
        id="ext:py:unresolved:value",
        kind="unresolved",
        sig="value",
        span=None,
        content_hash="h_val",
    )
    yaml_node = NodeCard(
        id="yaml:config.yaml::database.host",
        kind="yaml_config",
        sig="database.host",
        span=Span(file="config.yaml", start=1, end=2),
        content_hash="h_yaml",
    )
    for n in (real_cls, ext_builtin, unresolved_node, yaml_node):
        graph.add_node(n)

    # Make ext_builtin have 10 edges, unresolved 5 edges, real_cls 2 edges
    for i in range(10):
        src_id = f"py:mod_{i}.py::fn"
        graph.add_node(NodeCard(id=src_id, kind="function", span=Span(file=f"mod_{i}.py", start=1, end=10), content_hash=f"h_{i}"))
        graph.add_edge(Edge(src=src_id, dst=ext_builtin.id, type=EdgeType.CALLS))
    for i in range(5):
        src_id = f"py:mod_u_{i}.py::fn"
        graph.add_node(NodeCard(id=src_id, kind="function", span=Span(file=f"mod_u_{i}.py", start=1, end=10), content_hash=f"hu_{i}"))
        graph.add_edge(Edge(src=src_id, dst=unresolved_node.id, type=EdgeType.READS))
    graph.add_edge(Edge(src="py:mod_0.py::fn", dst=real_cls.id, type=EdgeType.CALLS))

    gods = god_nodes(graph, top_n=5)
    # Neither len, nor value, nor yaml should be in god nodes despite higher degree
    god_ids = [g["id"] for g in gods]
    assert "ext:py:builtin:len" not in god_ids
    assert "ext:py:unresolved:value" not in god_ids
    assert "yaml:config.yaml::database.host" not in god_ids
    # The application class should be listed
    assert "py:core/app.py::Application" in god_ids


def test_graph_diff():
    old_graph = _build_test_graph()
    new_graph = _build_test_graph()

    # Modify an existing node
    new_graph.nodes["py:core/engine.py::Engine"].content_hash = "new_hash_engine"

    # Add a new node and edge
    new_node = NodeCard(
        id="py:core/cache.py::Cache",
        kind="class",
        sig="Cache",
        span=Span(file="core/cache.py", start=1, end=20),
        content_hash="hash_cache",
    )
    new_graph.add_node(new_node)
    new_graph.add_edge(Edge(src="py:core/engine.py::Engine", dst=new_node.id, type=EdgeType.CALLS))

    # Remove an edge
    new_graph.edges = [e for e in new_graph.edges if e.src != "py:core/worker.py::Worker"]

    diff = graph_diff(old_graph, new_graph)
    assert diff["added_nodes_count"] == 1
    assert diff["modified_nodes_count"] == 1
    assert diff["added_edges_count"] == 1
    assert diff["removed_edges_count"] == 1
