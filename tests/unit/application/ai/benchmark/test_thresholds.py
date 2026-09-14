"""
Unit tests for M80 benchmark quality thresholds.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_news_digest.application.ai.benchmark.models import (
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkTask,
    QualityScore,
)
from ai_news_digest.application.ai.benchmark.thresholds import (
    QualityThresholds,
    ThresholdEvaluationResult,
    evaluate_thresholds,
)


class TestQualityThresholds:
    def test_default_thresholds(self):
        thresholds = QualityThresholds()
        assert thresholds.min_structured_validity == 0.8
        assert thresholds.min_overall_quality == 0.5
        assert thresholds.max_failure_rate == 0.3
        assert thresholds.min_success_rate == 0.7

    def test_custom_thresholds(self):
        thresholds = QualityThresholds(min_overall_quality=0.9, max_failure_rate=0.1)
        assert thresholds.min_overall_quality == 0.9
        assert thresholds.max_failure_rate == 0.1


class TestEvaluateThresholds:
    def test_passing_run(self):
        run = BenchmarkRun(
            run_id="run-1",
            dataset_version="v1",
            benchmark_version="m80-v1",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            total_requests=10,
            successes=9,
            failures=1,
        )
        thresholds = QualityThresholds(
            min_overall_quality=0.0,
            max_failure_rate=0.5,
            min_success_rate=0.5,
        )
        result = evaluate_thresholds(run, thresholds)
        assert isinstance(result, ThresholdEvaluationResult)
        assert result.passed is True

    def test_failing_success_rate(self):
        run = BenchmarkRun(
            run_id="run-1",
            dataset_version="v1",
            benchmark_version="m80-v1",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            total_requests=10,
            successes=3,
            failures=7,
        )
        result = evaluate_thresholds(run)
        assert result.passed is False
        assert any("success_rate" in f for f in result.failures)

    def test_no_requests_fails(self):
        run = BenchmarkRun(
            run_id="run-1",
            dataset_version="v1",
            benchmark_version="m80-v1",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            total_requests=0,
            successes=0,
            failures=0,
        )
        result = evaluate_thresholds(run)
        assert result.passed is False
        assert "no_requests_executed" in result.failures

    def test_task_score_thresholds(self):
        run = BenchmarkRun(
            run_id="run-1",
            dataset_version="v1",
            benchmark_version="m80-v1",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            total_requests=2,
            successes=2,
            failures=0,
        )
        run.results.append(
            BenchmarkResult(
                provider_id="openai",
                model="gpt-4",
                case_id="c1",
                task=BenchmarkTask.SUMMARY,
                quality_score=QualityScore(task=BenchmarkTask.SUMMARY, score=0.1),
            )
        )
        thresholds = QualityThresholds(
            min_overall_quality=0.0,
            max_failure_rate=1.0,
            min_success_rate=0.0,
            min_summary_score=0.5,
        )
        result = evaluate_thresholds(run, thresholds)
        assert result.passed is False
        assert any("summary_score" in f for f in result.failures)

    def test_failure_rate_above_threshold(self):
        run = BenchmarkRun(
            run_id="run-1",
            dataset_version="v1",
            benchmark_version="m80-v1",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            total_requests=10,
            successes=5,
            failures=5,
        )
        thresholds = QualityThresholds(
            min_overall_quality=0.0,
            max_failure_rate=0.1,
            min_success_rate=0.0,
        )
        result = evaluate_thresholds(run, thresholds)
        assert result.passed is False
        assert any("failure_rate" in f for f in result.failures)
