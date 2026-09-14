"""
Benchmark report generation for M80.

Generates machine-readable JSON reports and deterministic comparison reports.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from ai_news_digest.application.ai.benchmark.evaluator import evaluate_benchmark_run
from ai_news_digest.application.ai.benchmark.models import (
    BenchmarkComparison,
    BenchmarkRun,
)


class BenchmarkReport:
    """Machine-readable benchmark result report."""

    def __init__(self, run: BenchmarkRun) -> None:
        self._run = run

    def to_dict(self) -> dict[str, Any]:
        run = self._run
        completed_at = run.completed_at or datetime.now(UTC)
        duration_seconds = (completed_at - run.started_at).total_seconds()

        task_score_summary: dict[str, dict[str, Any]] = {}
        evaluation = evaluate_benchmark_run(run)
        for key, ts in evaluation.get("task_scores", {}).items():
            task_score_summary[key] = {
                "cases_evaluated": ts.cases_evaluated,
                "cases_passed": ts.cases_passed,
                "cases_failed": ts.cases_failed,
                "mean_score": round(ts.mean_score, 4),
                "min_score": round(ts.min_score, 4),
                "max_score": round(ts.max_score, 4),
            }

        provider_stats: dict[str, dict[str, Any]] = {}
        for result in run.results:
            pid = result.provider_id
            if pid not in provider_stats:
                provider_stats[pid] = {
                    "requests": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_latency_ms": 0.0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "total_cost": 0.0,
                    "cost_known_count": 0,
                }
            ps = provider_stats[pid]
            ps["requests"] += 1
            if result.failure is None:
                ps["successes"] += 1
            else:
                ps["failures"] += 1
            ps["total_latency_ms"] += result.latency_ms
            ps["total_input_tokens"] += result.input_tokens
            ps["total_output_tokens"] += result.output_tokens
            if result.cost_known:
                ps["total_cost"] += result.estimated_cost
                ps["cost_known_count"] += 1

        failure_breakdown: dict[str, int] = {}
        for result in run.results:
            if result.failure is not None:
                key = result.failure.category.value
                failure_breakdown[key] = failure_breakdown.get(key, 0) + 1

        return {
            "benchmark_version": run.benchmark_version,
            "dataset_version": run.dataset_version,
            "run_id": run.run_id,
            "timestamp": completed_at.isoformat(),
            "duration_seconds": round(duration_seconds, 3),
            "configuration": run.config,
            "providers_tested": list(run.provider_ids),
            "models_tested": list(run.model_ids),
            "cases_tested": list(run.case_ids),
            "tasks_tested": list(run.task_ids),
            "total_requests": run.total_requests,
            "successes": run.successes,
            "failures": run.failures,
            "provider_stats": provider_stats,
            "task_scores": task_score_summary,
            "failure_breakdown": failure_breakdown,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class ComparisonReport:
    """Deterministic comparison layer for provider/model results."""

    def __init__(self, run: BenchmarkRun) -> None:
        self._run = run

    def build(self) -> list[BenchmarkComparison]:
        comparisons: dict[tuple[str, str], dict[str, Any]] = {}

        for result in self._run.results:
            if result.failure is not None:
                continue
            key = (result.provider_id, result.model)
            if key not in comparisons:
                comparisons[key] = {
                    "scores": [],
                    "structured": [],
                    "summary": [],
                    "takeaways": [],
                    "why_it_matters": [],
                    "categories": [],
                    "companies": [],
                    "topics": [],
                    "latencies": [],
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                    "cost_known_count": 0,
                    "cases": 0,
                }
            c = comparisons[key]
            c["cases"] += 1
            c["input_tokens"] += result.input_tokens
            c["output_tokens"] += result.output_tokens
            c["latencies"].append(result.latency_ms)
            if result.cost_known:
                c["cost"] += result.estimated_cost
                c["cost_known_count"] += 1
            if result.quality_score is None:
                continue
            score = result.quality_score.score
            task = result.quality_score.task.value
            c["scores"].append(score)
            if task == "structured_output_validity":
                c["structured"].append(score)
            elif task == "summary":
                c["summary"].append(score)
            elif task == "key_takeaways":
                c["takeaways"].append(score)
            elif task == "why_it_matters":
                c["why_it_matters"].append(score)
            elif task == "categories":
                c["categories"].append(score)
            elif task == "companies":
                c["companies"].append(score)
            elif task == "topics":
                c["topics"].append(score)

        output: list[BenchmarkComparison] = []
        for (provider_id, model), c in comparisons.items():

            def _mean(vals: list[float]) -> float:
                return sum(vals) / len(vals) if vals else 0.0

            def _median(vals: list[float]) -> float | None:
                if not vals:
                    return None
                s = sorted(vals)
                n = len(s)
                if n % 2 == 1:
                    return s[n // 2]
                return (s[n // 2 - 1] + s[n // 2]) / 2.0

            overall = _mean(c["scores"])
            cost_known = c["cost_known_count"] > 0
            output.append(
                BenchmarkComparison(
                    provider_id=provider_id,
                    model=model,
                    overall_quality=round(overall, 4),
                    structured_validity=round(_mean(c["structured"]), 4),
                    summary_score=round(_mean(c["summary"]), 4),
                    takeaways_score=round(_mean(c["takeaways"]), 4),
                    why_it_matters_score=round(_mean(c["why_it_matters"]), 4),
                    category_f1=round(_mean(c["categories"]), 4),
                    company_f1=round(_mean(c["companies"]), 4),
                    topic_f1=round(_mean(c["topics"]), 4),
                    success_rate=round(self._run.successes / self._run.total_requests, 4)
                    if self._run.total_requests > 0
                    else 0.0,
                    median_latency_ms=_median(c["latencies"]),
                    total_input_tokens=c["input_tokens"],
                    total_output_tokens=c["output_tokens"],
                    estimated_cost=round(c["cost"], 4),
                    cost_known=cost_known,
                    cases_evaluated=c["cases"],
                )
            )
        return output

    def to_dict(self) -> dict[str, Any]:
        comparisons = self.build()
        return {
            "comparisons": [
                {
                    "provider_id": c.provider_id,
                    "model": c.model,
                    "overall_quality": c.overall_quality,
                    "structured_validity": c.structured_validity,
                    "summary_score": c.summary_score,
                    "takeaways_score": c.takeaways_score,
                    "why_it_matters_score": c.why_it_matters_score,
                    "category_f1": c.category_f1,
                    "company_f1": c.company_f1,
                    "topic_f1": c.topic_f1,
                    "success_rate": c.success_rate,
                    "median_latency_ms": c.median_latency_ms,
                    "total_input_tokens": c.total_input_tokens,
                    "total_output_tokens": c.total_output_tokens,
                    "estimated_cost": c.estimated_cost,
                    "cost_known": c.cost_known,
                    "cases_evaluated": c.cases_evaluated,
                }
                for c in comparisons
            ]
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def generate_benchmark_report(run: BenchmarkRun) -> BenchmarkReport:
    return BenchmarkReport(run)


def generate_comparison_report(run: BenchmarkRun) -> ComparisonReport:
    return ComparisonReport(run)


__all__ = [
    "BenchmarkReport",
    "ComparisonReport",
    "generate_benchmark_report",
    "generate_comparison_report",
]
