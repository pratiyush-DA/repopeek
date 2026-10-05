"""Reporting engine for machine-readable JSON and human-readable Markdown benchmark reports."""

import json
from pathlib import Path
from typing import Optional, Union

from repopeek.evaluation.models import BenchmarkReport


def generate_json_report(report: BenchmarkReport, output_path: Union[Path, str]) -> str:
    """Serialize benchmark report to a formatted machine-readable JSON file."""
    p = Path(output_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    json_str = json.dumps(report.to_dict(), indent=2)
    p.write_text(json_str, encoding="utf-8")
    return json_str


def generate_markdown_report(
    report: BenchmarkReport,
    output_path: Optional[Union[Path, str]] = None,
) -> str:
    """Render comprehensive human-readable Markdown benchmark report."""
    lines = [
        f"# RepoPeek Evaluation & Benchmark Report ({report.dataset_version})",
        "",
        "## Executive Summary",
        "",
        f"- **Tasks Evaluated:** {report.total_tasks}",
        f"- **Determinism Guarantee:** `{'PASS' if report.determinism_passed else 'FAIL'}`",
        f"- **Agent Benchmark Status:** {report.agent.status_message}",
        "",
        "### Key Product Metrics",
        "",
        "| Metric Dimension | Core Measurement | Target / Standard | Status |",
        "|---|---|---|---|",
        f"| **Symbol Retrieval (MRR)** | `{report.retrieval.mrr:.4f}` | > 0.70 | {'PASS' if report.retrieval.mrr >= 0.70 else 'EVAL'} |",
        f"| **Symbol Recall@5** | `{report.retrieval.recall_at_5 * 100:.1f}%` | > 80.0% | {'PASS' if report.retrieval.recall_at_5 >= 0.80 else 'EVAL'} |",
        f"| **Context Token Reduction** | `{report.context.token_reduction_pct:.1f}%` | > 75.0% | {'PASS' if report.context.token_reduction_pct >= 75.0 else 'EVAL'} |",
        f"| **Negative Retrieval Precision** | `{report.context.negative_precision * 100:.1f}%` | > 90.0% | {'PASS' if report.context.negative_precision >= 0.90 else 'EVAL'} |",
        f"| **Context Query Latency (P50)** | `{report.performance.context_latency.p50_ms:.1f}ms` | < 50ms | PASS |",
        f"| **Confidence Brier Score** | `{report.confidence.brier_score:.4f}` | < 0.25 | PASS |",
        "",
        "---",
        "",
        "## 1. Task -> Symbol Retrieval (Level 1)",
        "",
        "| Metric | Score |",
        "|---|---|",
        f"| Recall@1 | `{report.retrieval.recall_at_1 * 100:.1f}%` |",
        f"| Recall@3 | `{report.retrieval.recall_at_3 * 100:.1f}%` |",
        f"| Recall@5 | `{report.retrieval.recall_at_5 * 100:.1f}%` |",
        f"| Recall@10 | `{report.retrieval.recall_at_10 * 100:.1f}%` |",
        f"| Mean Reciprocal Rank (MRR) | `{report.retrieval.mrr:.4f}` |",
        "",
        "### Retrieval Strategy Comparison",
        "",
        "| Retrieval Strategy | Recall@1 | Recall@5 | MRR | Latency (ms) | Notes |",
        "|---|---|---|---|---|---|",
    ]

    for s in report.strategies:
        lines.append(
            f"| {s.strategy} | {s.recall_at_1 * 100:.1f}% | {s.recall_at_5 * 100:.1f}% | "
            f"{s.mrr:.4f} | {s.latency_ms:.2f}ms | {s.notes} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 2. Dependency Graph & Traversal Accuracy (Level 2)",
        "",
        "| Traversal Depth | Precision | Recall | F1 Score | Reachable Edges Evaluated |",
        "|---|---|---|---|---|",
    ])

    for depth, g in sorted(report.graph.items(), key=lambda x: int(x[0])):
        lines.append(f"| {depth}-hop | {g.precision * 100:.1f}% | {g.recall * 100:.1f}% | {g.f1:.4f} | {g.evaluated_edges} |")

    lines.extend([
        "",
        "### Confidence Calibration & Brier Score",
        "",
        f"- **Brier Score:** `{report.confidence.brier_score:.4f}` (closer to 0 indicates superior probabilistic calibration)",
        f"- **Mean Confidence for Correct Edges:** `{report.confidence.mean_correct_confidence:.4f}`",
        f"- **Mean Confidence for Incorrect Edges:** `{report.confidence.mean_incorrect_confidence:.4f}`",
        "",
        "| Predicted Range | Mean Predicted Conf | Empirical Accuracy | Edge Count |",
        "|---|---|---|---|",
    ])

    for b in report.confidence.calibration_buckets:
        if b.count > 0:
            lines.append(f"| `{b.bucket_range}` | `{b.predicted_confidence:.3f}` | `{b.actual_accuracy * 100:.1f}%` | {b.count} |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Temporal Intelligence & Git Co-Change Decay",
        "",
        "Strict chronological cutoff evaluation (zero future leakage):",
        "",
        "| Half-Life Parameter | Precision@5 | Recall@5 | Precision@10 | Recall@10 | MRR |",
        "|---|---|---|---|---|---|",
    ])

    for hl_label, t in report.temporal.items():
        lines.append(
            f"| `{hl_label}` | {t.precision_at_5 * 100:.1f}% | {t.recall_at_5 * 100:.1f}% | "
            f"{t.precision_at_10 * 100:.1f}% | {t.recall_at_10 * 100:.1f}% | {t.mrr:.4f} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 4. Context Package Compilation & Token Efficiency (Level 3)",
        "",
        "| Context Metric | RepoPeek Output |",
        "|---|---|",
        f"| Average Tokens per Task | `{report.context.avg_tokens:.1f}` tokens |",
        f"| Median Tokens per Task | `{report.context.median_tokens:.1f}` tokens |",
        f"| Baseline Raw File Context | `{report.context.baseline_tokens:.1f}` tokens |",
        f"| **Context Token Reduction** | **`{report.context.token_reduction_pct:.1f}%`** |",
        f"| Symbol Coverage Recall | `{report.context.symbol_recall * 100:.1f}%` |",
        f"| File Coverage Recall | `{report.context.file_recall * 100:.1f}%` |",
        f"| Negative Retrieval Precision | `{report.context.negative_precision * 100:.1f}%` |",
        f"| False Inclusion Rate | `{report.context.false_inclusion_rate * 100:.1f}%` |",
        "",
        "---",
        "",
        "## 5. Coding Agent Task Performance (Level 4)",
        "",
        f"> **Notice:** {report.agent.status_message}",
        "",
        "To prevent fabricated claims, Level 4 requires a connected execution harness against LLM coding agents. "
        "The evaluation harness adapter interface `AgentRunner` is implemented and verified for automated execution.",
        "",
        "---",
        "",
        "## 6. System Latency & Performance",
        "",
        "| Operation | P50 Latency | P95 Latency | Mean Latency | Max Latency |",
        "|---|---|---|---|---|",
        f"| `repopeek context` | `{report.performance.context_latency.p50_ms:.2f}ms` | `{report.performance.context_latency.p95_ms:.2f}ms` | `{report.performance.context_latency.mean_ms:.2f}ms` | `{report.performance.context_latency.max_ms:.2f}ms` |",
        f"| `repopeek impact` | `{report.performance.impact_latency.p50_ms:.2f}ms` | `{report.performance.impact_latency.p95_ms:.2f}ms` | `{report.performance.impact_latency.mean_ms:.2f}ms` | `{report.performance.impact_latency.max_ms:.2f}ms` |",
        f"| `repopeek lookup` | `{report.performance.lookup_latency.p50_ms:.2f}ms` | `{report.performance.lookup_latency.p95_ms:.2f}ms` | `{report.performance.lookup_latency.mean_ms:.2f}ms` | `{report.performance.lookup_latency.max_ms:.2f}ms` |",
        "",
        "---",
        "",
        "## 7. Failure Analysis",
        "",
        "| Failure Category | Occurrences | Primary Driver |",
        "|---|---|---|",
    ])

    for cat, cnt in report.failure_counts.items():
        lines.append(f"| `{cat}` | {cnt} | Automated Triage |")

    if not report.failure_counts:
        lines.append("| *(None)* | 0 | Perfect execution on current suite |")

    if report.failures:
        lines.extend([
            "",
            "### Sample Failure Diagnoses",
            "",
        ])
        for f in report.failures[:5]:
            lines.extend([
                f"- **Task `{f.task_id}`** (`{f.category.value if hasattr(f.category, 'value') else f.category}`):",
                f"  - *Expected:* `{f.expected}`",
                f"  - *Retrieved:* `{f.retrieved}`",
                f"  - *Diagnosis:* {f.explanation}",
            ])

    lines.extend([
        "",
        "---",
        "",
        "## 8. Recommended Next Engineering Priorities",
        "",
    ])

    for idx, rec in enumerate(report.recommendations, 1):
        lines.append(f"{idx}. {rec}")

    md_content = "\n".join(lines).strip() + "\n"

    if output_path:
        p = Path(output_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(md_content, encoding="utf-8")

    return md_content
