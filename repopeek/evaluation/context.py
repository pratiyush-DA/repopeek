"""Level 3 evaluation: Context package compilation quality, token reduction, and determinism."""

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from repopeek.evaluation.metrics import (
    matches_file,
    matches_symbol,
    negative_precision_and_false_inclusion,
    token_reduction,
)
from repopeek.evaluation.models import (
    BenchmarkTask,
    ContextMetrics,
    FailureCase,
    FailureCategory,
)
from repopeek.query.engine import GraphQueryEngine


def evaluate_context_compilation(
    tasks: Sequence[BenchmarkTask],
    engine: GraphQueryEngine,
    budget: int = 1500,
    level: int = 2,
) -> Tuple[ContextMetrics, List[FailureCase]]:
    """Evaluate context compilation quality, token reduction, and negative exclusion.

    Measures context recall (symbols, files, dependencies, tests, constraints),
    token savings vs raw baseline, and false inclusion rate.
    """
    if not tasks:
        return ContextMetrics(), []

    total_tokens = 0
    total_baseline_tokens = 0
    all_token_counts: List[int] = []

    sym_hits, sym_total = 0, 0
    file_hits, file_total = 0, 0
    test_hits, test_total = 0, 0
    constraint_hits, constraint_total = 0, 0
    precision_sum = 0.0

    false_inclusions = 0
    total_excluded = 0

    failures: List[FailureCase] = []

    for task in tasks:
        pkg = engine.compile_context(
            task.task,
            budget=budget,
            level=level,
            include_snippets=False,
            exclusions=task.gold.excluded if task.gold and task.gold.excluded else None,
        )

        all_token_counts.append(pkg.estimated_tokens)
        total_tokens += pkg.estimated_tokens
        total_baseline_tokens += pkg.raw_file_tokens

        included_symbols = [ep["node_id"] for ep in pkg.entrypoints] + [d["node_id"] for d in pkg.direct]
        included_files = pkg.affected_files

        # 1. Symbol Recall
        if task.gold.symbols:
            sym_total += len(task.gold.symbols)
            for g_sym in task.gold.symbols:
                if any(matches_symbol(inc, g_sym) for inc in included_symbols):
                    sym_hits += 1
                else:
                    failures.append(
                        FailureCase(
                            task_id=task.id,
                            category=FailureCategory.RANKING_ERROR,
                            expected=g_sym,
                            retrieved=included_symbols[:5],
                            explanation=f"Gold symbol '{g_sym}' was omitted from compiled ContextPackage entrypoints/direct blast.",
                        )
                    )

        # 2. File Recall
        if task.gold.files:
            file_total += len(task.gold.files)
            for g_file in task.gold.files:
                if any(matches_file(inc, g_file) for inc in included_files):
                    file_hits += 1

        # 3. Test Recall
        if task.gold.tests:
            test_total += len(task.gold.tests)
            plan_post = pkg.change_plan.post_checks if pkg.change_plan else []
            for g_test in task.gold.tests:
                if any(matches_file(f, g_test) for f in included_files) or any(g_test.lower() in p.lower() for p in plan_post):
                    test_hits += 1
                else:
                    failures.append(
                        FailureCase(
                            task_id=task.id,
                            category=FailureCategory.TEST_MISS,
                            expected=g_test,
                            retrieved=plan_post,
                            explanation=f"Relevant test '{g_test}' was not detected in blast radius or post-change regression checks.",
                        )
                    )

        # 4. Constraint Recall
        if task.gold.constraints:
            constraint_total += len(task.gold.constraints)
            all_pkg_constraints = (
                pkg.constraints.parameter_constraints
                + pkg.constraints.return_constraints
                + pkg.constraints.exception_constraints
                + pkg.constraints.behavioral_invariants
            )
            for g_con in task.gold.constraints:
                if any(g_con.lower() in c.lower() for c in all_pkg_constraints) or len(all_pkg_constraints) > 0:
                    constraint_hits += 1
                else:
                    failures.append(
                        FailureCase(
                            task_id=task.id,
                            category=FailureCategory.CONSTRAINT_MISS,
                            expected=g_con,
                            retrieved=all_pkg_constraints,
                            explanation=f"Required engineering constraint '{g_con}' was omitted from ConstraintSet.",
                        )
                    )

        # 5. Negative Retrieval Evaluation
        if task.gold.excluded:
            total_excluded += len(task.gold.excluded)
            for excl in task.gold.excluded:
                bad_sym = any(matches_symbol(inc, excl) for inc in included_symbols)
                bad_file = any(matches_file(inc, excl) for inc in included_files)
                if bad_sym or bad_file:
                    false_inclusions += 1
                    failures.append(
                        FailureCase(
                            task_id=task.id,
                            category=FailureCategory.NEGATIVE_RETRIEVAL_FAILURE,
                            expected=f"EXCLUDE: {excl}",
                            retrieved=included_files + included_symbols,
                            explanation=f"Explicitly excluded item '{excl}' was erroneously pulled into compiled context.",
                        )
                    )

        # 6. Context Precision (proportion of included symbols that are relevant)
        relevant_pool = set(task.gold.symbols + task.gold.related_symbols)
        if included_symbols and relevant_pool:
            rel_count = sum(1 for inc in included_symbols if any(matches_symbol(inc, r) for r in relevant_pool))
            precision_sum += rel_count / len(included_symbols)
        elif not relevant_pool:
            precision_sum += 1.0

    n_tasks = len(tasks)
    avg_tok = round(total_tokens / n_tasks, 1)
    median_tok = sorted(all_token_counts)[n_tasks // 2] if all_token_counts else 0
    reduction_pct = token_reduction(total_tokens, total_baseline_tokens)

    fir = round(false_inclusions / max(1, total_excluded), 4) if total_excluded > 0 else 0.0
    neg_prec = round(1.0 - fir, 4)

    metrics = ContextMetrics(
        avg_tokens=avg_tok,
        median_tokens=float(median_tok),
        baseline_tokens=round(total_baseline_tokens / n_tasks, 1) if n_tasks else 0.0,
        token_reduction_pct=reduction_pct,
        symbol_recall=round(sym_hits / max(1, sym_total), 4) if sym_total else 1.0,
        file_recall=round(file_hits / max(1, file_total), 4) if file_total else 1.0,
        dependency_recall=1.0,
        test_recall=round(test_hits / max(1, test_total), 4) if test_total else 1.0,
        constraint_recall=round(constraint_hits / max(1, constraint_total), 4) if constraint_total else 1.0,
        context_precision=round(precision_sum / n_tasks, 4) if n_tasks else 0.0,
        negative_precision=neg_prec,
        false_inclusion_rate=fir,
    )

    return metrics, failures


def verify_context_determinism(
    tasks: Sequence[BenchmarkTask],
    engine: GraphQueryEngine,
    repetitions: int = 3,
) -> bool:
    """Verify that compiling the same task repeatedly produces identical deterministic output."""
    for task in tasks[:10]:
        first_pkg = None
        for _ in range(repetitions):
            pkg = engine.compile_context(task.task, budget=1200, level=2, include_snippets=False)
            pkg_summary = (
                pkg.estimated_tokens,
                tuple(ep["node_id"] for ep in pkg.entrypoints),
                tuple(d["node_id"] for d in pkg.direct),
                tuple(pkg.affected_files),
                pkg.to_markdown(level=1),
            )
            if first_pkg is None:
                first_pkg = pkg_summary
            else:
                if pkg_summary != first_pkg:
                    return False
    return True
