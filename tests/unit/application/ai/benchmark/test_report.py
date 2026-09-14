"""
Unit tests for M80 benchmark reports.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from ai_news_digest.application.ai.benchmark.models import (
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkTask,
    QualityScore,
)
from ai_news_digest.application.ai.benchmark.report import (
    BenchmarkReport,
    ComparisonReport,
)
from ai_news_digest.application.ai.benchmark.thresholds import (
    QualityThresholds,
    evaluate_thresholds,
)


class TestBenchmarkReport:
    def test_to_dict_contains_expected_keys(self):
        run = BenchmarkRun(
            run_id="run-1",
            dataset_version="v1",
            benchmark_version="m80-v1",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            total_requests=2,
            successes=1,
            failures=1,
        )
        run.results.append(
            BenchmarkResult(
                provider_id="openai",
                model="gpt-4",
                case_id="c1",
                task=BenchmarkTask.SUMMARY,
                quality_score=QualityScore(task=BenchmarkTask.SUMMARY, score=0.8),
            )
        )
        report = BenchmarkReport(run)
        data = report.to_dict()
        assert data["benchmark_version"] == "m80-v1"
        assert data["total_requests"] == 2
        assert data["successes"] == 1
        assert data["failures"] == 1
        assert "task_scores" in data

    def test_to_json_is_valid_json(self):
        run = BenchmarkRun(
            run_id="run-1",
            dataset_version="v1",
            benchmark_version="m80-v1",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        report = BenchmarkReport(run)
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["run_id"] == "run-1"


class TestComparisonReport:
    def test_build_returns_comparisons(self):
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
                quality_score=QualityScore(task=BenchmarkTask.SUMMARY, score=0.9),
            )
        )
        run.results.append(
            BenchmarkResult(
                provider_id="openai",
                model="gpt-4",
                case_id="c2",
                task=BenchmarkTask.CATEGORIES,
                quality_score=QualityScore(task=BenchmarkTask.CATEGORIES, score=1.0),
            )
        )
        comparison = ComparisonReport(run)
        comparisons = comparison.build()
        assert len(comparisons) == 1
        assert comparisons[0].provider_id == "openai"
        assert comparisons[0].success_rate == 1.0

    def test_to_json_is_valid_json(self):
        run = BenchmarkRun(
            run_id="run-1",
            dataset_version="v1",
            benchmark_version="m80-v1",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        comparison = ComparisonReport(run)
        json_str = comparison.to_json()
        parsed = json.loads(json_str)
        assert "comparisons" in parsed


class TestThresholdEvaluation:
    def test_passing_thresholds(self):
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
        run.results.append(
            BenchmarkResult(
                provider_id="openai",
                model="gpt-4",
                case_id="c1",
                task=BenchmarkTask.SUMMARY,
                quality_score=QualityScore(task=BenchmarkTask.SUMMARY, score=0.8),
            )
        )
        run.overall_score = None
        thresholds = QualityThresholds(
            min_overall_quality=0.0,
            max_failure_rate=0.5,
            min_success_rate=0.5,
        )
        result = evaluate_thresholds(run, thresholds)
        assert result.passed is True

    def test_failing_failure_rate(self):
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
        thresholds = QualityThresholds(max_failure_rate=0.1)
        result = evaluate_thresholds(run, thresholds)
        assert result.passed is False
        assert any("failure_rate" in f for f in result.failures)

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
