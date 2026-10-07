"""Unit tests verifying PR20 retrieval reliability, conservative stemming,

identifier normalization, multi-component scoring, and hard negative pruning.
"""

from typing import Dict, List
import pytest

from repopeek.graph.blast_radius import (
    compute_blast_radius,
    is_node_excluded,
)
from repopeek.models.schema import (
    CanonicalGraph,
    Confidence,
    Edge,
    EdgeType,
    Evidence,
    NodeCard,
    Span,
)
from repopeek.retrieval.intent import (
    RetrievalScore,
    compute_retrieval_score,
    extract_task_identifiers,
    generate_identifier_variants,
    normalize_task_text,
    normalize_term_stem,
    resolve_task_to_symbols,
)


def test_stemming_plurals():
    """Verify conservative plural normalization without over-stemming."""
    assert normalize_term_stem("payments") == "payment"
    assert normalize_term_stem("attempts") == "attempt"
    assert normalize_term_stem("endpoints") == "endpoint"
    assert normalize_term_stem("retries") == "retry"
    assert normalize_term_stem("queries") == "query"
    assert normalize_term_stem("dependencies") == "dependency"
    assert normalize_term_stem("processes") == "process"
    assert normalize_term_stem("watches") == "watch"


def test_stemming_verbs():
    """Verify verb suffix normalization for -ing and -ed."""
    assert normalize_term_stem("retrying") == "retry"
    assert normalize_term_stem("retried") == "retry"
    assert normalize_term_stem("parsing") == "parse"
    assert normalize_term_stem("parsed") == "parse"
    assert normalize_term_stem("validating") == "validate"
    assert normalize_term_stem("validated") == "validate"
    assert normalize_term_stem("processing") == "process"


def test_stemming_nominalizations():
    """Verify nominalization normalization for -ation and -tion."""
    assert normalize_term_stem("validation") == "validate"
    assert normalize_term_stem("calculation") == "calculate"
    assert normalize_term_stem("connection") == "connect"
    assert normalize_term_stem("extraction") == "extract"


def test_stemming_agent_nouns():
    """Verify agent noun mapping for common software roles."""
    assert normalize_term_stem("parser") == "parse"
    assert normalize_term_stem("validator") == "validate"
    assert normalize_term_stem("validators") == "validate"
    assert normalize_term_stem("processor") == "process"
    assert normalize_term_stem("miner") == "mine"
    assert normalize_term_stem("compiler") == "compile"


def test_stemming_conservative_preservation():
    """Ensure non-plural 's' words are never mutilated."""
    assert normalize_term_stem("class") == "class"
    assert normalize_term_stem("status") == "status"
    assert normalize_term_stem("basis") == "basis"
    assert normalize_term_stem("analysis") == "analysis"
    assert normalize_term_stem("redis") == "redis"


def test_identifier_casing_variants():
    """Verify snake_case, camelCase, PascalCase, and SCREAMING_SNAKE_CASE share normalized concepts."""
    snake_vars = set(generate_identifier_variants("retry_payment"))
    camel_vars = set(generate_identifier_variants("retryPayment"))
    pascal_vars = set(generate_identifier_variants("RetryPayment"))
    screaming_vars = set(generate_identifier_variants("RETRY_PAYMENT"))

    # All representations must decompose into common concept tokens
    assert "retry" in snake_vars and "payment" in snake_vars
    assert "retry" in camel_vars and "payment" in camel_vars
    assert "retry" in pascal_vars and "payment" in pascal_vars
    assert "retry" in screaming_vars and "payment" in screaming_vars

    # Cross-casing variants generated
    assert "RetryPayment" in snake_vars
    assert "retry_payment" in camel_vars
    assert "retry_payment" in pascal_vars


def test_kebab_and_dotted_identifiers():
    """Verify kebab-case and dot-notation decompose accurately."""
    kebab_vars = set(generate_identifier_variants("retry-payment-task"))
    assert "retry_payment_task" in kebab_vars
    assert "retry" in kebab_vars

    dot_vars = set(generate_identifier_variants("PaymentProcessor.retry_payment"))
    assert "PaymentProcessor" in dot_vars
    assert "retry_payment" in dot_vars
    assert "retry" in dot_vars
    assert "payment" in dot_vars


def test_compound_variant_generation():
    """Verify adjacent query concepts produce engineering compound terms."""
    intent = extract_task_identifiers("Change payment retry logic from 3 to 5 attempts")
    assert "payment" in intent.concepts
    assert "retry" in intent.concepts
    assert any("payment_retry" in c or "retry_payment" in c for c in intent.compounds)


def test_technical_verbs_preserved_as_concepts():
    """Ensure technical verbs (parse, validate, test) are indexed as search concepts."""
    intent = extract_task_identifiers("Validate invoice payload and parse XML buffer")
    assert "validate" in intent.verbs
    assert "parse" in intent.verbs
    assert "validate" in intent.concepts
    assert "parse" in intent.concepts


def test_retrieval_score_exact_match_priority():
    """Verify exact symbol match dominates raw lexical matches."""
    intent = extract_task_identifiers("Update InvoiceParser.parse implementation")
    node_data_exact = {
        "kind": "method",
        "sig": "def parse(self, content: str)",
        "file": "src/billing/invoice.py",
        "story": "Parses invoices",
    }
    node_data_partial = {
        "kind": "function",
        "sig": "def parse_xml_helper(buffer)",
        "file": "src/utils/xml.py",
        "story": "Helper that parses XML buffer data",
    }

    score_exact = compute_retrieval_score(
        "src/billing/invoice.py::InvoiceParser.parse",
        node_data_exact,
        intent,
        bm25_rank_map={"src/billing/invoice.py::InvoiceParser.parse": 2},
    )
    score_partial = compute_retrieval_score(
        "src/utils/xml.py::parse_xml_helper",
        node_data_partial,
        intent,
        bm25_rank_map={"src/utils/xml.py::parse_xml_helper": 0},  # Rank 0 in BM25
    )

    assert score_exact.exact_match > 0.0
    assert score_exact.total > score_partial.total


def test_retrieval_score_identifier_outranks_weak_bm25():
    """Verify strong identifier match outranks weak lexical co-occurrence."""
    intent = extract_task_identifiers("Modify calculate_path_confidence decay")
    node_match = {
        "kind": "function",
        "sig": "def calculate_path_confidence(step_confidences)",
        "file": "repopeek/graph/blast_radius.py",
    }
    node_cooccurrence = {
        "kind": "function",
        "sig": "def format_path(path)",
        "file": "repopeek/storage/cache.py",
        "story": "Calculates and modifies path formatting with decay factors",
    }

    score_id = compute_retrieval_score(
        "repopeek/graph/blast_radius.py::calculate_path_confidence",
        node_match,
        intent,
        bm25_rank_map={},
    )
    score_cooc = compute_retrieval_score(
        "repopeek/storage/cache.py::format_path",
        node_cooccurrence,
        intent,
        bm25_rank_map={"repopeek/storage/cache.py::format_path": 1},
    )

    assert score_id.identifier > 0.5
    assert score_id.total > score_cooc.total


def test_hard_negative_exclusion_directory():
    """Verify directory exclusions match subpaths and prefixes."""
    node = NodeCard(
        id="sample::scripts/run_pipeline.sh",
        kind="script",
        name="run_pipeline.sh",
        span=Span(file="scripts/run_pipeline.sh", start=1, end=20),
        content_hash="mock1",
    )
    assert is_node_excluded("sample::scripts/run_pipeline.sh", node, ["scripts/"])
    assert is_node_excluded("sample::scripts/run_pipeline.sh", node, ["scripts"])
    assert not is_node_excluded("sample::src/billing/invoice.py", None, ["scripts/"])


def test_hard_negative_exclusion_file():
    """Verify file exclusions match exact file paths and names."""
    node = NodeCard(
        id="sample::db/queries.sql::query_invoices",
        kind="sql_query",
        name="query_invoices",
        span=Span(file="db/queries.sql", start=1, end=10),
        content_hash="mock2",
    )
    assert is_node_excluded("sample::db/queries.sql::query_invoices", node, ["db/queries.sql"])
    assert is_node_excluded("sample::db/queries.sql::query_invoices", node, ["queries.sql"])
    assert not is_node_excluded("sample::src/billing/invoice.py", None, ["db/queries.sql"])


def test_hard_negative_exclusion_symbol():
    """Verify symbol exclusions match qualified and unqualified symbol names."""
    node = NodeCard(
        id="sample::src/models/base.py::AuditableEntity",
        kind="class",
        name="AuditableEntity",
        span=Span(file="src/models/base.py", start=10, end=40),
        content_hash="mock3",
    )
    assert is_node_excluded("sample::src/models/base.py::AuditableEntity", node, ["AuditableEntity"])
    assert not is_node_excluded("sample::src/billing/invoice.py::Invoice", None, ["AuditableEntity"])


def test_hard_negative_exclusion_glob():
    """Verify glob pattern exclusions match wildcard paths."""
    node = NodeCard(
        id="sample::tests/shipping/test_calculator.py",
        kind="module",
        name="test_calculator.py",
        span=Span(file="tests/shipping/test_calculator.py", start=1, end=50),
        content_hash="mock4",
    )
    assert is_node_excluded("sample::tests/shipping/test_calculator.py", node, ["**/shipping/**"])
    assert is_node_excluded("sample::tests/shipping/test_calculator.py", node, ["tests/*"])


def test_hard_negative_pruning_stops_downstream_leak():
    """Verify hard negative pruning stops traversal immediately at the excluded node."""
    # Graph: A -> B -> C where B is in an excluded directory
    nodes = {
        "A": NodeCard(id="A", kind="function", name="billing_func", span=Span(file="src/billing/invoice.py", start=1, end=10), content_hash="hA"),
        "B": NodeCard(id="B", kind="function", name="shipping_func", span=Span(file="shipping/calculator.py", start=1, end=10), content_hash="hB"),
        "C": NodeCard(id="C", kind="function", name="carrier_func", span=Span(file="shipping/carrier.py", start=1, end=10), content_hash="hC"),
    }
    edges = [
        Edge(src="A", dst="B", type=EdgeType.CALLS, confidence=Confidence.RESOLVED, evidence=Evidence(file="src/billing/invoice.py", start_line=5, end_line=5, how_derived="ast_call")),
        Edge(src="B", dst="C", type=EdgeType.CALLS, confidence=Confidence.RESOLVED, evidence=Evidence(file="shipping/calculator.py", start_line=5, end_line=5, how_derived="ast_call")),
    ]
    graph = CanonicalGraph(nodes=nodes, edges=edges)

    report = compute_blast_radius(graph, target_id="A", exclusions=["shipping/"])

    affected_node_ids = {n.node_id for n in report.direct + report.indirect}
    # Neither B nor C should ever appear in affected nodes or affected files
    assert "B" not in affected_node_ids
    assert "C" not in affected_node_ids
    assert "shipping/calculator.py" not in report.affected_files
    assert "shipping/carrier.py" not in report.affected_files

    # B must be captured in report.excluded
    excluded_node_ids = {e.node_id for e in report.excluded}
    assert "B" in excluded_node_ids
    # C was never reached at all because traversal pruned B before queue expansion
    assert "C" not in excluded_node_ids


def test_retrieval_determinism():
    """Verify that multiple retrieval resolutions with identical inputs yield identical rankings."""
    node_index = {
        "node_1": {"kind": "function", "sig": "def process_payment(amount)"},
        "node_2": {"kind": "method", "sig": "def retry_payment(self)"},
        "node_3": {"kind": "class", "sig": "class PaymentProcessor"},
    }
    task = "Change payment retry attempts"

    res1 = resolve_task_to_symbols(task, node_index, fts_results=[("node_2", 10.0), ("node_3", 8.0)])
    res2 = resolve_task_to_symbols(task, node_index, fts_results=[("node_2", 10.0), ("node_3", 8.0)])

    assert len(res1) == len(res2)
    for c1, c2 in zip(res1, res2):
        assert c1.node_id == c2.node_id
        assert c1.score == c2.score
        assert c1.breakdown == c2.breakdown


def test_candidate_recall_and_ablation_execution():
    """Verify that ablation runner executes configurations without crashing and returns results."""
    from repopeek.evaluation.models import BenchmarkTask, GoldReference
    from repopeek.evaluation.retrieval import run_retrieval_ablation
    from repopeek.query.engine import GraphQueryEngine

    task = BenchmarkTask(
        id="t1",
        task="Change payment retry logic",
        gold=GoldReference(symbols=["node_2"]),
    )
    nodes = {
        "node_1": NodeCard(id="node_1", kind="function", name="process", span=Span(file="f1.py", start=1, end=5), content_hash="h1"),
        "node_2": NodeCard(id="node_2", kind="function", name="retry_payment", span=Span(file="f2.py", start=1, end=5), content_hash="h2"),
    }
    graph = CanonicalGraph(nodes=nodes, edges=[])
    engine = GraphQueryEngine(graph=graph)

    ablations = run_retrieval_ablation([task], engine)
    assert len(ablations) == 4
    config_names = [a.configuration for a in ablations]
    assert "Baseline" in config_names
    assert "Experiment A" in config_names
    assert "Experiment B" in config_names
    assert "Experiment C" in config_names


def test_context_compiler_prunes_excluded_entrypoints():
    """Verify that ContextCompiler discards entrypoints matching explicit negative exclusions."""
    from repopeek.context.compiler import ContextCompiler
    from repopeek.query.engine import GraphQueryEngine

    nodes = {
        "shipping::service.py::ShippingService": NodeCard(
            id="shipping::service.py::ShippingService",
            kind="class",
            name="ShippingService",
            span=Span(file="shipping/service.py", start=1, end=50),
            content_hash="hs1",
        ),
        "billing::invoice.py::Invoice": NodeCard(
            id="billing::invoice.py::Invoice",
            kind="class",
            name="Invoice",
            span=Span(file="billing/invoice.py", start=1, end=50),
            content_hash="hb1",
        ),
    }
    graph = CanonicalGraph(nodes=nodes, edges=[])
    engine = GraphQueryEngine(graph=graph)
    compiler = ContextCompiler(engine)

    pkg = compiler.compile(
        task="Update invoice without modifying shipping",
        exclusions=["shipping/"],
    )

    entrypoint_ids = [ep["node_id"] for ep in pkg.entrypoints]
    assert "shipping::service.py::ShippingService" not in entrypoint_ids
    assert not any("shipping" in f for f in pkg.affected_files)
    if pkg.excluded:
        assert any("shipping::service.py::ShippingService" in ex["node_id"] for ex in pkg.excluded)
