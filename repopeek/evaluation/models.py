"""Data models and schemas for RepoPeek evaluation and benchmarking."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FailureCategory(str, Enum):
    """Taxonomy of benchmark failure modes for automated triage."""
    LEXICAL_MISS = "LEXICAL_MISS"
    IDENTIFIER_MISS = "IDENTIFIER_MISS"
    RANKING_ERROR = "RANKING_ERROR"
    GRAPH_MISSING_EDGE = "GRAPH_MISSING_EDGE"
    GRAPH_FALSE_EDGE = "GRAPH_FALSE_EDGE"
    HTTP_BOUNDARY_MISS = "HTTP_BOUNDARY_MISS"
    TEMPORAL_MISS = "TEMPORAL_MISS"
    CONSTRAINT_MISS = "CONSTRAINT_MISS"
    TEST_MISS = "TEST_MISS"
    NEGATIVE_RETRIEVAL_FAILURE = "NEGATIVE_RETRIEVAL_FAILURE"


@dataclass
class FailureCase:
    """A detailed failure instance for error analysis and triage."""
    task_id: str
    category: FailureCategory
    expected: Any
    retrieved: Any
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "category": self.category.value if hasattr(self.category, "value") else str(self.category),
            "expected": self.expected,
            "retrieved": self.retrieved,
            "explanation": self.explanation,
        }


@dataclass
class GoldReference:
    """Ground truth reference metadata for a benchmark task."""
    symbols: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    related_symbols: List[str] = field(default_factory=list)
    dependencies: List[Dict[str, str]] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    excluded: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkTask:
    """A single evaluation task in the benchmark suite."""
    id: str
    task: str
    repository: str = "sample_repo"
    category: str = "A. Local behavior"
    gold: GoldReference = field(default_factory=GoldReference)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task": self.task,
            "repository": self.repository,
            "category": self.category,
            "gold": self.gold.to_dict(),
        }


@dataclass
class RetrievalMetrics:
    """Recall and ranking metrics for task-to-symbol resolution."""
    recall_at_1: float = 0.0
    recall_at_3: float = 0.0
    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    mrr: float = 0.0
    total_tasks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyComparison:
    """Performance and accuracy metrics comparing retrieval approaches."""
    strategy: str
    recall_at_1: float
    recall_at_5: float
    mrr: float
    latency_ms: float
    index_size_bytes: int = 0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GraphDepthMetrics:
    """Accuracy metrics for dependency graph traversal at a specific hop depth."""
    depth: int
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    evaluated_edges: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CalibrationBucket:
    """A confidence calibration bucket comparing predicted vs actual accuracy."""
    bucket_range: str
    predicted_confidence: float
    actual_accuracy: float
    count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConfidenceMetrics:
    """Statistical calibration and Brier score evaluation."""
    brier_score: float = 0.0
    calibration_buckets: List[CalibrationBucket] = field(default_factory=list)
    mean_correct_confidence: float = 0.0
    mean_incorrect_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "brier_score": self.brier_score,
            "calibration_buckets": [b.to_dict() for b in self.calibration_buckets],
            "mean_correct_confidence": self.mean_correct_confidence,
            "mean_incorrect_confidence": self.mean_incorrect_confidence,
        }


@dataclass
class TemporalMetrics:
    """Predictive accuracy of Git temporal co-change intelligence."""
    half_life_days: float
    precision_at_5: float = 0.0
    recall_at_5: float = 0.0
    precision_at_10: float = 0.0
    recall_at_10: float = 0.0
    mrr: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContextMetrics:
    """Quality and token reduction metrics for ContextPackage compilation."""
    avg_tokens: float = 0.0
    median_tokens: float = 0.0
    baseline_tokens: float = 0.0
    token_reduction_pct: float = 0.0
    symbol_recall: float = 0.0
    file_recall: float = 0.0
    dependency_recall: float = 0.0
    test_recall: float = 0.0
    constraint_recall: float = 0.0
    context_precision: float = 0.0
    negative_precision: float = 1.0
    false_inclusion_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LatencyMetrics:
    """Latency distribution metrics in milliseconds."""
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    mean_ms: float = 0.0
    max_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PerformanceReport:
    """Execution timing and indexing latency benchmarks."""
    context_latency: LatencyMetrics = field(default_factory=LatencyMetrics)
    impact_latency: LatencyMetrics = field(default_factory=LatencyMetrics)
    lookup_latency: LatencyMetrics = field(default_factory=LatencyMetrics)
    indexing_time_sec: float = 0.0
    incremental_indexing_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_latency": self.context_latency.to_dict(),
            "impact_latency": self.impact_latency.to_dict(),
            "lookup_latency": self.lookup_latency.to_dict(),
            "indexing_time_sec": self.indexing_time_sec,
            "incremental_indexing_time_ms": self.incremental_indexing_time_ms,
        }


@dataclass
class AgentResult:
    """Quantitative outcome of an agent executing an engineering task."""
    task_id: str
    agent_mode: str  # "baseline" or "repopeek_assisted"
    success: bool
    tokens: int
    tool_calls: int
    files_inspected: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    wrong_edits: List[str] = field(default_factory=list)
    tests_passed: bool = False
    elapsed_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentComparison:
    """Controlled comparison between baseline and RepoPeek-assisted agent execution."""
    evaluated: bool = False
    status_message: str = "Agent-level improvement has NOT been demonstrated yet."
    baseline_summary: Dict[str, Any] = field(default_factory=dict)
    repopeek_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BenchmarkReport:
    """Comprehensive benchmark evaluation report."""
    dataset_version: str = "v1"
    total_tasks: int = 0
    retrieval: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    strategies: List[StrategyComparison] = field(default_factory=list)
    graph: Dict[int, GraphDepthMetrics] = field(default_factory=dict)
    confidence: ConfidenceMetrics = field(default_factory=ConfidenceMetrics)
    temporal: Dict[str, TemporalMetrics] = field(default_factory=dict)
    context: ContextMetrics = field(default_factory=ContextMetrics)
    determinism_passed: bool = True
    performance: PerformanceReport = field(default_factory=PerformanceReport)
    agent: AgentComparison = field(default_factory=AgentComparison)
    failures: List[FailureCase] = field(default_factory=list)
    failure_counts: Dict[str, int] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "total_tasks": self.total_tasks,
            "retrieval": self.retrieval.to_dict(),
            "strategies": [s.to_dict() for s in self.strategies],
            "graph": {str(k): v.to_dict() for k, v in self.graph.items()},
            "confidence": self.confidence.to_dict(),
            "temporal": {k: v.to_dict() for k, v in self.temporal.items()},
            "context": self.context.to_dict(),
            "determinism_passed": self.determinism_passed,
            "performance": self.performance.to_dict(),
            "agent": self.agent.to_dict(),
            "failures": [f.to_dict() for f in self.failures],
            "failure_counts": self.failure_counts,
            "recommendations": self.recommendations,
        }
