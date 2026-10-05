"""RepoPeek Evaluation and Benchmarking Subsystem."""

from repopeek.evaluation.benchmark import AgentRunner, BenchmarkRunner, MockAgentRunner
from repopeek.evaluation.dataset import BenchmarkDataset
from repopeek.evaluation.models import (
    BenchmarkReport,
    BenchmarkTask,
    CalibrationBucket,
    ConfidenceMetrics,
    ContextMetrics,
    FailureCase,
    FailureCategory,
    GoldReference,
    GraphDepthMetrics,
    RetrievalMetrics,
    StrategyComparison,
    TemporalMetrics,
)
from repopeek.evaluation.report import generate_json_report, generate_markdown_report

__all__ = [
    "AgentRunner",
    "BenchmarkDataset",
    "BenchmarkReport",
    "BenchmarkRunner",
    "BenchmarkTask",
    "CalibrationBucket",
    "ConfidenceMetrics",
    "ContextMetrics",
    "FailureCase",
    "FailureCategory",
    "GoldReference",
    "GraphDepthMetrics",
    "MockAgentRunner",
    "RetrievalMetrics",
    "StrategyComparison",
    "TemporalMetrics",
    "generate_json_report",
    "generate_markdown_report",
]
