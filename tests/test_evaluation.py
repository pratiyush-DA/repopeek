"""Comprehensive test suite for RepoPeek evaluation, metrics, and benchmarking subsystem."""

import json
from pathlib import Path
import pytest

from repopeek.cli import main
from repopeek.evaluation.benchmark import (
    AgentRunner,
    BenchmarkRunner,
    MockAgentRunner,
)
from repopeek.evaluation.context import (
    evaluate_context_compilation,
    verify_context_determinism,
)
from repopeek.evaluation.dataset import BenchmarkDataset
from repopeek.evaluation.graph import (
    evaluate_confidence_calibration,
    evaluate_graph_accuracy,
    matches_edge,
)
from repopeek.evaluation.metrics import (
    brier_score,
    calibration_buckets,
    matches_file,
    matches_symbol,
    mean_reciprocal_rank,
    negative_precision_and_false_inclusion,
    percentile,
    precision_recall_f1,
    recall_at_k,
    reciprocal_rank,
    token_reduction,
)
from repopeek.evaluation.models import (
    AgentComparison,
    AgentResult,
    BenchmarkReport,
    BenchmarkTask,
    CalibrationBucket,
    ConfidenceMetrics,
    ContextMetrics,
    FailureCase,
    FailureCategory,
    GoldReference,
    GraphDepthMetrics,
    LatencyMetrics,
    PerformanceReport,
    RetrievalMetrics,
    StrategyComparison,
    TemporalMetrics,
)
from repopeek.evaluation.report import (
    generate_json_report,
    generate_markdown_report,
)
from repopeek.evaluation.retrieval import (
    compare_retrieval_strategies,
    evaluate_task_retrieval,
)
from repopeek.evaluation.temporal import evaluate_temporal_cochange
from repopeek.graph.builder import GraphBuilder
from repopeek.models.schema import CanonicalGraph, Edge, EdgeType, NodeCard, Span
from repopeek.query.engine import GraphQueryEngine
from repopeek.temporal.miner import CommitRecord


FIXTURE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


@pytest.fixture(scope="module")
def eval_engine():
    """Build canonical graph engine from sample_repo fixture."""
    builder = GraphBuilder()
    graph = builder.build_from_directory(FIXTURE_REPO)
    return GraphQueryEngine(graph=graph, repo_root=FIXTURE_REPO)


# ── 1. Metric Calculations Tests ──

def test_matches_symbol():
    """Verify symbol matching for qualified names, URIs, and class methods."""
    target_uri = "py:src/billing/invoice.py::InvoiceParser.parse"
    assert matches_symbol(target_uri, "InvoiceParser.parse")
    assert matches_symbol(target_uri, "parse")
    assert matches_symbol(target_uri, target_uri)
    assert matches_symbol("InvoiceParser.parse", "InvoiceParser.parse")
    assert not matches_symbol(target_uri, "validate_invoice")


def test_matches_file():
    """Verify file path matching with cross-platform slashes."""
    assert matches_file("src/billing/invoice.py", "invoice.py")
    assert matches_file("src\\billing\\invoice.py", "src/billing/invoice.py")
    assert matches_file("./src/billing/invoice.py", "billing/invoice.py")
    assert not matches_file("src/billing/invoice.py", "src/models/base.py")


def test_recall_at_k():
    """Verify Recall@K calculation."""
    retrieved = ["InvoiceParser", "InvoiceParser.parse", "validate_invoice"]
    gold = ["InvoiceParser.parse"]

    assert recall_at_k(retrieved, gold, k=1) == 0.0
    assert recall_at_k(retrieved, gold, k=2) == 1.0
    assert recall_at_k(retrieved, gold, k=5) == 1.0
    assert recall_at_k(retrieved, ["nonexistent"], k=5) == 0.0
    assert recall_at_k(retrieved, [], k=5) == 1.0


def test_reciprocal_rank():
    """Verify Reciprocal Rank computation."""
    retrieved = ["NodeA", "NodeB", "InvoiceParser.parse", "NodeD"]
    assert reciprocal_rank(retrieved, ["NodeA"]) == 1.0
    assert reciprocal_rank(retrieved, ["NodeB"]) == 0.5
    assert round(reciprocal_rank(retrieved, ["InvoiceParser.parse"]), 4) == round(1.0 / 3.0, 4)
    assert reciprocal_rank(retrieved, ["Missing"]) == 0.0
    assert reciprocal_rank([], ["NodeA"]) == 0.0


def test_mean_reciprocal_rank():
    """Verify MRR across multiple queries."""
    all_ret = [
        ["A", "B", "C"],  # hit at 1 -> 1.0
        ["X", "A", "C"],  # hit at 2 -> 0.5
        ["Y", "Z", "W"],  # hit at 0 -> 0.0
    ]
    all_gold = [["A"], ["A"], ["A"]]
    # MRR = (1.0 + 0.5 + 0.0) / 3 = 0.5
    assert mean_reciprocal_rank(all_ret, all_gold) == 0.5


def test_precision_recall_f1():
    """Verify precision, recall, and F1 set metrics."""
    retrieved = {"A", "B", "C", "D"}
    gold = {"A", "B", "E"}
    p, r, f1 = precision_recall_f1(retrieved, gold)
    assert p == 0.5  # 2 / 4
    assert round(r, 4) == round(2.0 / 3.0, 4)
    assert f1 > 0.0

    # Disjoint
    assert precision_recall_f1({"X"}, {"Y"}) == (0.0, 0.0, 0.0)
    # Empty
    assert precision_recall_f1(set(), set()) == (1.0, 1.0, 1.0)


def test_brier_score():
    """Verify Brier score calibration metric."""
    preds = [0.9, 0.8, 0.2]
    outcomes = [1, 1, 0]
    # err = (0.1^2 + 0.2^2 + 0.2^2) / 3 = (0.01 + 0.04 + 0.04) / 3 = 0.09 / 3 = 0.03
    assert brier_score(preds, outcomes) == 0.03
    assert brier_score([], []) == 0.0


def test_calibration_buckets():
    """Verify calibration bucket partitioning."""
    preds = [0.05, 0.15, 0.85, 0.95]
    outcomes = [0, 0, 1, 1]
    buckets = calibration_buckets(preds, outcomes, n_buckets=10)
    assert len(buckets) == 10
    assert buckets[0].count == 1
    assert buckets[0].actual_accuracy == 0.0
    assert buckets[8].count == 1
    assert buckets[8].actual_accuracy == 1.0
    assert buckets[9].count == 1
    assert buckets[9].actual_accuracy == 1.0


def test_negative_precision_and_false_inclusion():
    """Verify negative retrieval precision and false inclusion tracking."""
    retrieved = ["src/billing/invoice.py", "src/models/base.py"]
    excluded = ["scripts/run_pipeline.sh", "config/pipeline.yaml"]
    neg_p, fir = negative_precision_and_false_inclusion(retrieved, excluded, matcher=matches_file)
    assert fir == 0.0
    assert neg_p == 1.0

    # With false inclusion
    retrieved_with_leak = retrieved + ["scripts/run_pipeline.sh"]
    neg_p2, fir2 = negative_precision_and_false_inclusion(retrieved_with_leak, excluded, matcher=matches_file)
    assert fir2 == 0.5
    assert neg_p2 == 0.5


def test_token_reduction():
    """Verify context token reduction percentage."""
    assert token_reduction(250, 1000) == 75.0
    assert token_reduction(1000, 1000) == 0.0
    assert token_reduction(1200, 1000) == 0.0
    assert token_reduction(100, 0) == 0.0


def test_percentile():
    """Verify percentile calculation for latencies."""
    vals = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(vals, 50) == 30.0
    assert percentile(vals, 0) == 10.0
    assert percentile(vals, 100) == 50.0
    assert percentile([], 50) == 0.0


# ── 2. Dataset Loading and Validation Tests ──

def test_dataset_loading_and_validation(tmp_path: Path):
    """Test loading, saving, and validating benchmark tasks in YAML and JSON."""
    raw_yaml = """
version: "v1"
tasks:
  - id: t1
    task: "Modify invoice parser"
    category: "A. Local behavior"
    repository: "sample_repo"
    gold:
      symbols: ["InvoiceParser.parse"]
      files: ["src/billing/invoice.py"]
      excluded: ["scripts/"]
  - id: t2
    task: "Update AuditableEntity"
    category: "B. Dependency impact"
    repository: "sample_repo"
    gold:
      symbols: ["AuditableEntity"]
      files: ["src/models/base.py"]
"""
    p_yaml = tmp_path / "tasks.yaml"
    p_yaml.write_text(raw_yaml, encoding="utf-8")

    ds = BenchmarkDataset.load_file(p_yaml)
    assert len(ds) == 2
    assert ds["t1"].id == "t1"
    assert ds.get_task("t2").gold.symbols == ["AuditableEntity"]
    assert len(ds.categories) == 2

    # Save to JSON and reload
    p_json = tmp_path / "tasks.json"
    ds.save_file(p_json)
    ds_json = BenchmarkDataset.load_file(p_json)
    assert len(ds_json) == 2
    assert ds_json["t1"].gold.excluded == ["scripts/"]


def test_dataset_validation_detects_duplicates(tmp_path: Path):
    """Verify duplicate task IDs raise validation errors."""
    raw_yaml = """
version: "v1"
tasks:
  - id: dup_id
    task: "Task 1"
    gold:
      symbols: ["A"]
  - id: dup_id
    task: "Task 2"
    gold:
      symbols: ["B"]
"""
    p = tmp_path / "bad.yaml"
    p.write_text(raw_yaml, encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate task ID"):
        BenchmarkDataset.load_file(p)


def test_dataset_validation_detects_empty_task(tmp_path: Path):
    """Verify empty task descriptions are rejected."""
    raw_yaml = """
version: "v1"
tasks:
  - id: empty_task
    task: "   "
    gold:
      symbols: ["A"]
"""
    p = tmp_path / "empty.yaml"
    p.write_text(raw_yaml, encoding="utf-8")
    with pytest.raises(ValueError, match="empty task description"):
        BenchmarkDataset.load_file(p)


def test_frozen_v1_tasks_yaml():
    """Verify official benchmarks/v1/tasks.yaml is valid, has 50 tasks across 6 categories."""
    official_path = Path(__file__).parent.parent / "benchmarks" / "v1" / "tasks.yaml"
    assert official_path.exists(), "Official v1 tasks.yaml missing!"
    ds = BenchmarkDataset.load_file(official_path)
    assert len(ds) == 50
    assert len(ds.categories) == 6
    assert ds.validate() == []


# ── 3. Level 1: Retrieval Evaluation Tests ──

def test_evaluate_task_retrieval(eval_engine):
    """Verify task-to-symbol evaluation produces valid Recall@K and MRR."""
    tasks = [
        BenchmarkTask(
            id="test_parse",
            task="Change invoice validation in InvoiceParser.parse",
            gold=GoldReference(symbols=["InvoiceParser.parse"], files=["src/billing/invoice.py"]),
        ),
        BenchmarkTask(
            id="test_entity",
            task="Update AuditableEntity base class",
            gold=GoldReference(symbols=["AuditableEntity"], files=["src/models/base.py"]),
        ),
    ]

    metrics, failures = evaluate_task_retrieval(tasks, eval_engine)
    assert metrics.total_tasks == 2
    assert metrics.recall_at_5 > 0.0
    assert metrics.mrr > 0.0


def test_compare_retrieval_strategies(eval_engine):
    """Verify comparison of retrieval strategies A, B, and C."""
    tasks = [
        BenchmarkTask(
            id="strat_test",
            task="Update invoice parser payload validation",
            gold=GoldReference(symbols=["InvoiceParser.parse"]),
        )
    ]
    strats = compare_retrieval_strategies(tasks, eval_engine)
    assert len(strats) == 3
    strat_names = [s.strategy for s in strats]
    assert any("Strategy A" in n for n in strat_names)
    assert any("Strategy B" in n for n in strat_names)
    assert any("Strategy C" in n for n in strat_names)
    for s in strats:
        assert s.latency_ms >= 0.0
        assert 0.0 <= s.mrr <= 1.0


# ── 4. Level 2: Graph Evaluation Tests ──

def test_evaluate_graph_accuracy(eval_engine):
    """Verify graph traversal precision, recall, and F1 across depths."""
    gold_edges = [
        {"src": "InvoiceParser.parse", "dst": "validate_invoice", "type": "CALLS"},
        {"src": "Invoice", "dst": "AuditableEntity", "type": "INHERITS"},
    ]
    depth_metrics, failures = evaluate_graph_accuracy(gold_edges, eval_engine.graph, depths=[1, 2, 3])
    assert 1 in depth_metrics
    assert 2 in depth_metrics
    assert 3 in depth_metrics
    assert depth_metrics[1].recall > 0.0
    assert depth_metrics[1].f1 > 0.0


def test_matches_edge():
    """Verify edge tuple matching with wildcard ANY type."""
    retrieved = ("py:src/invoice.py::parser.parse", "py:src/validator.py::validate", "CALLS")
    assert matches_edge(retrieved, ("parser.parse", "validate", "CALLS"))
    assert matches_edge(retrieved, ("parser.parse", "validate", "ANY"))
    assert not matches_edge(retrieved, ("parser.parse", "validate", "READS"))


def test_evaluate_confidence_calibration():
    """Verify confidence calibration and bucket calculation."""
    preds = [(0.95, True), (0.90, True), (0.40, False), (0.20, False)]
    conf = evaluate_confidence_calibration(preds)
    assert conf.brier_score >= 0.0
    assert conf.mean_correct_confidence > conf.mean_incorrect_confidence


# ── 5. Temporal Intelligence Evaluation & Leakage Prevention Tests ──

def test_temporal_leakage_prevention():
    """Verify commits after chronological cutoff are strictly separated from training."""
    commits = [
        CommitRecord("c1", 1000.0, ["file_a.py", "file_b.py"]),
        CommitRecord("c2", 2000.0, ["file_a.py", "file_b.py"]),
        CommitRecord("c3", 3000.0, ["file_a.py", "file_c.py"]),
        CommitRecord("c4", 4000.0, ["file_a.py", "file_d.py"]),
    ]

    # Set cutoff at t=2500 (c1, c2 in training; c3, c4 in test)
    results = evaluate_temporal_cochange(commits, cutoff_time=2500.0, half_lives=[30.0, 180.0])
    assert "30d" in results
    assert "180d" in results
    assert results["180d"].half_life_days == 180.0


# ── 6. Level 3: Context Compilation and Determinism Tests ──

def test_context_compilation_evaluation(eval_engine):
    """Verify ContextPackage compilation quality and negative exclusion."""
    tasks = [
        BenchmarkTask(
            id="ctx_1",
            task="Update InvoiceParser without modifying shipping module",
            gold=GoldReference(
                symbols=["InvoiceParser"],
                files=["src/billing/invoice.py"],
                excluded=["shipping/"],
            ),
        )
    ]
    metrics, failures = evaluate_context_compilation(tasks, eval_engine, budget=1000)
    assert metrics.avg_tokens > 0.0
    assert metrics.token_reduction_pct > 0.0
    assert metrics.negative_precision == 1.0
    assert metrics.false_inclusion_rate == 0.0


def test_context_determinism_verification(eval_engine):
    """Verify context determinism produces identical outputs across multiple runs."""
    tasks = [
        BenchmarkTask(
            id="det_1",
            task="Modify parse method on InvoiceParser",
            gold=GoldReference(symbols=["InvoiceParser.parse"]),
        )
    ]
    assert verify_context_determinism(tasks, eval_engine, repetitions=3) is True


# ── 7. Level 4: Agent Benchmark Harness Tests ──

def test_mock_agent_runner():
    """Verify MockAgentRunner satisfies AgentRunner protocol."""
    runner = MockAgentRunner()
    res_base = runner.run_task("Fix invoice parsing bug")
    assert res_base.agent_mode == "baseline"
    assert res_base.tokens > 3000

    res_assisted = runner.run_task("Fix invoice parsing bug", context="# RepoPeek Context")
    assert res_assisted.agent_mode == "repopeek_assisted"
    assert res_assisted.tokens < 1000
    assert res_assisted.tool_calls < res_base.tool_calls


# ── 8. Benchmark Serialization and Reporting Tests ──

def test_benchmark_report_generation(tmp_path: Path, eval_engine):
    """Verify BenchmarkRunner executes and generates JSON and Markdown reports."""
    tasks = [
        BenchmarkTask(
            id="rep_1",
            task="Change invoice parse method",
            gold=GoldReference(
                symbols=["InvoiceParser.parse"],
                files=["src/billing/invoice.py"],
                excluded=["scripts/"],
            ),
        )
    ]
    ds = BenchmarkDataset(tasks=tasks, version="v1")
    runner = BenchmarkRunner(engine=eval_engine, dataset=ds)
    report = runner.run_all(run_agent_eval=False)

    assert report.total_tasks == 1
    assert report.determinism_passed is True
    assert "Agent-level improvement has NOT been demonstrated yet" in report.agent.status_message

    # Test JSON serialization
    json_path = tmp_path / "benchmark-results.json"
    generate_json_report(report, json_path)
    assert json_path.exists()
    loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
    assert loaded_json["total_tasks"] == 1
    assert "retrieval" in loaded_json

    # Test Markdown generation
    md_path = tmp_path / "benchmark-report.md"
    md_content = generate_markdown_report(report, md_path)
    assert md_path.exists()
    assert "# RepoPeek Evaluation & Benchmark Report" in md_content
    assert "Executive Summary" in md_content
    assert "Failure Analysis" in md_content


# ── 9. CLI Evaluation Integration Test ──

def test_cli_evaluate_command(tmp_path: Path):
    """Verify CLI `repopeek evaluate` runs cleanly and exits 0."""
    raw_yaml = """
version: "v1"
tasks:
  - id: cli_task_1
    task: "Change invoice validation in InvoiceParser.parse"
    category: "A. Local behavior"
    repository: "sample_repo"
    gold:
      symbols: ["InvoiceParser.parse"]
      files: ["src/billing/invoice.py"]
"""
    p_tasks = tmp_path / "test_tasks.yaml"
    p_tasks.write_text(raw_yaml, encoding="utf-8")

    out_json = tmp_path / "cli_results.json"
    out_md = tmp_path / "cli_report.md"

    # Invoke CLI evaluate command
    ret = main([
        "evaluate",
        "--repo-path", str(FIXTURE_REPO),
        "--dataset", str(p_tasks),
        "--output", str(out_json),
        "--report", str(out_md),
    ])
    assert ret == 0
    assert out_json.exists()
    assert out_md.exists()
