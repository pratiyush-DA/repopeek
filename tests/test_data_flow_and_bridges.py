"""Unit tests for RepoPeek Def-Use Data Flow, Config Readers, and Cross-Language Bridges."""

from pathlib import Path
import pytest

from repopeek.graph.builder import GraphBuilder
from repopeek.graph.lenses import (
    get_bridges_lens,
    get_config_lens,
    get_data_entity_lens,
    get_data_lens,
    get_process_lens,
    trace_impact,
    trace_variable_flow,
)
from repopeek.models.schema import Confidence, EdgeType

SAMPLE_REPO_DIR = Path("tests/fixtures/sample_repo")


@pytest.fixture(scope="module")
def sample_graph():
    builder = GraphBuilder()
    return builder.build_from_directory(SAMPLE_REPO_DIR, repo_commit="commit_pr6")


def test_cross_language_python_to_sql_bridge(sample_graph):
    """Verify Python code embedding SQL queries resolves directly to SQL schema table cards."""
    parse_id = "py:src/billing/invoice.py::InvoiceParser.parse"
    table_id = "sql:db/queries.sql::table.invoices"

    # Embedded SQL statement edge
    embed_edges = [
        e for e in sample_graph.edges
        if e.src == parse_id and e.type == EdgeType.EMBEDS_SQL
    ]
    assert len(embed_edges) == 1
    query_node_id = embed_edges[0].dst
    assert "query_L" in query_node_id

    # Direct and query-level READS bridge to SQL table
    reads_table_edges = [
        e for e in sample_graph.edges
        if e.dst == table_id and e.type == EdgeType.READS and e.confidence == Confidence.RESOLVED
    ]
    reading_sources = {e.src for e in reads_table_edges}
    assert parse_id in reading_sources
    assert query_node_id in reading_sources


def test_cross_language_shell_and_yaml_bridges(sample_graph):
    """Verify Shell running Python and YAML invoking Shell pipeline scripts."""
    # Shell -> Python
    shell_runs = [
        e for e in sample_graph.edges
        if "run_pipeline.sh" in e.src and e.type == EdgeType.RUNS_SCRIPT
    ]
    assert len(shell_runs) >= 1
    assert any("invoice.py" in e.dst for e in shell_runs)
    assert any(e.confidence == Confidence.RESOLVED for e in shell_runs)

    # YAML -> Shell
    yaml_runs = [
        e for e in sample_graph.edges
        if "pipeline.yaml" in e.src and e.type == EdgeType.RUNS_SCRIPT
    ]
    assert len(yaml_runs) >= 1
    assert any("run_pipeline.sh" in e.dst for e in yaml_runs)


def test_config_reader_binding(sample_graph):
    """Verify code reading config keys binds to JSON/YAML config node cards."""
    init_id = "py:src/billing/invoice.py::InvoiceParser.__init__"
    config_key_id = "json:config/app_config.json::database.dialect"

    config_reads = [
        e for e in sample_graph.edges
        if e.src == init_id and e.dst == config_key_id and e.type == EdgeType.READS
    ]
    assert len(config_reads) == 1
    assert config_reads[0].confidence == Confidence.RESOLVED
    assert config_reads[0].evidence.how_derived == "ast_config_read"


def test_env_reader_binding(sample_graph):
    """Verify code reading environment variables binds to export locations in scripts."""
    init_id = "py:src/billing/invoice.py::InvoiceParser.__init__"

    env_reads = [
        e for e in sample_graph.edges
        if e.src == init_id and "run_pipeline.sh" in e.dst and e.type == EdgeType.READS
    ]
    assert len(env_reads) >= 1
    assert any(e.confidence == Confidence.RESOLVED for e in env_reads)


def test_variable_def_use_data_flow(sample_graph):
    """Verify instance and class variables record definitions, writes, and reads."""
    cache_var_id = "py:src/billing/invoice.py::InvoiceParser._cache"
    assert cache_var_id in sample_graph.nodes
    assert sample_graph.nodes[cache_var_id].kind == "variable"

    flow = trace_variable_flow(sample_graph, "_cache")
    assert flow["variable"] == cache_var_id
    assert "py:src/billing/invoice.py::InvoiceParser" in flow["defined_in"]
    assert "py:src/billing/invoice.py::InvoiceParser.__init__" in flow["writers"]
    assert "py:src/billing/invoice.py::InvoiceParser.parse" in flow["readers"]


def test_blast_radius_impact_trace(sample_graph):
    """Verify upstream blast radius traversal answers impact questions."""
    table_id = "sql:db/queries.sql::table.invoices"
    impact = trace_impact(sample_graph, table_id)

    assert impact["target"] == table_id
    assert impact["total_affected"] >= 2
    assert "py:src/billing/invoice.py::InvoiceParser.parse" in impact["by_kind"]["functions"]


def test_all_specialized_lenses(sample_graph):
    """Verify all specialized lenses project cleanly with valid integrity."""
    # Data lens
    data_lens = get_data_lens(sample_graph)
    assert len(data_lens.nodes) >= 10
    assert all(e.type in (EdgeType.READS, EdgeType.WRITES, EdgeType.DEFINED_IN) for e in data_lens.edges)

    # Data Entity lens
    entity_lens = get_data_entity_lens(sample_graph)
    assert len(entity_lens.nodes) >= 5
    assert all(
        e.type in (EdgeType.READS, EdgeType.WRITES, EdgeType.EMBEDS_SQL)
        for e in entity_lens.edges
    )

    # Config lens
    config_lens = get_config_lens(sample_graph)
    assert len(config_lens.nodes) >= 5
    assert any("database.dialect" in nid for nid in config_lens.nodes)

    # Process lens
    process_lens = get_process_lens(sample_graph)
    assert len(process_lens.nodes) >= 3
    assert any(e.type == EdgeType.RUNS_SCRIPT for e in process_lens.edges)

    # Bridges lens
    bridges_lens = get_bridges_lens(sample_graph)
    assert len(bridges_lens.nodes) >= 5
    assert len(bridges_lens.edges) >= 4

    # Verify no dangling edges in any lens
    for lens in (data_lens, entity_lens, config_lens, process_lens, bridges_lens):
        node_ids = set(lens.nodes.keys())
        for e in lens.edges:
            assert e.src in node_ids
            assert e.dst in node_ids
