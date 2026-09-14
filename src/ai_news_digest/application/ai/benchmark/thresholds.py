"""
Quality threshold configuration and evaluation for M80 benchmarks.

Thresholds are configurable and act as benchmark acceptance criteria only.
They do not affect normal application operation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_news_digest.application.ai.benchmark.models import (
    BenchmarkRun,
    TaskScore,
)


@dataclass(slots=True)
class QualityThresholds:
    """Configurable quality thresholds for benchmark validation."""

    min_structured_validity: float = 0.8
    min_overall_quality: float = 0.5
    max_failure_rate: float = 0.3
    min_summary_score: float = 0.3
    min_takeaways_score: float = 0.3
    min_why_it_matters_score: float = 0.2
    min_category_f1: float = 0.5
    min_company_f1: float = 0.5
    min_topic_f1: float = 0.5
    min_success_rate: float = 0.7


@dataclass(frozen=True, slots=True)
class ThresholdEvaluationResult:
    """Result of evaluating a benchmark run against thresholds."""

    passed: bool
    failures: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)


def evaluate_thresholds(
    run: BenchmarkRun,
    thresholds: QualityThresholds | None = None,
) -> ThresholdEvaluationResult:
    """Evaluate a benchmark run against quality thresholds."""
    if thresholds is None:
        thresholds = QualityThresholds()

    failures: list[str] = []
    details: dict[str, Any] = {}

    if run.total_requests <= 0:
        failures.append("no_requests_executed")
        return ThresholdEvaluationResult(passed=False, failures=tuple(failures), details=details)

    success_rate = run.successes / run.total_requests
    details["success_rate"] = round(success_rate, 4)
    if success_rate < thresholds.min_success_rate:
        failures.append(f"success_rate_below_{thresholds.min_success_rate}")

    if run.overall_score is not None:
        overall = run.overall_score.overall_mean
        details["overall_mean"] = round(overall, 4)
        if overall < thresholds.min_overall_quality:
            failures.append(f"overall_quality_below_{thresholds.min_overall_quality}")

    task_scores: dict[str, TaskScore] = {}
    for result in run.results:
        if result.quality_score is None:
            continue
        key = result.quality_score.task.value
        if key not in task_scores:
            task_scores[key] = TaskScore(task=result.quality_score.task)
        task_scores[key].cases_evaluated += 1
        task_scores[key].total_score += result.quality_score.score
        if result.quality_score.score >= 0.5:
            task_scores[key].cases_passed += 1
        else:
            task_scores[key].cases_failed += 1

    for key, ts in task_scores.items():
        if ts.cases_evaluated > 0:
            ts.mean_score = ts.total_score / ts.cases_evaluated
        details[key] = {
            "cases_evaluated": ts.cases_evaluated,
            "mean_score": round(ts.mean_score, 4),
        }

        if (
            key == "structured_output_validity"
            and ts.mean_score < thresholds.min_structured_validity
        ):
            failures.append(f"structured_validity_below_{thresholds.min_structured_validity}")
        if key == "summary" and ts.mean_score < thresholds.min_summary_score:
            failures.append(f"summary_score_below_{thresholds.min_summary_score}")
        if key == "key_takeaways" and ts.mean_score < thresholds.min_takeaways_score:
            failures.append(f"takeaways_score_below_{thresholds.min_takeaways_score}")
        if key == "why_it_matters" and ts.mean_score < thresholds.min_why_it_matters_score:
            failures.append(f"why_it_matters_score_below_{thresholds.min_why_it_matters_score}")

    failure_rate = run.failures / run.total_requests if run.total_requests > 0 else 0.0
    details["failure_rate"] = round(failure_rate, 4)
    if failure_rate > thresholds.max_failure_rate:
        failures.append(f"failure_rate_above_{thresholds.max_failure_rate}")

    return ThresholdEvaluationResult(
        passed=len(failures) == 0,
        failures=tuple(failures),
        details=details,
    )


__all__ = [
    "QualityThresholds",
    "ThresholdEvaluationResult",
    "evaluate_thresholds",
]
