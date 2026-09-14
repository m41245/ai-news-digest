"""
Unit tests for M80 benchmark models.
"""

from __future__ import annotations

from datetime import UTC

import pytest

from ai_news_digest.application.ai.benchmark.models import (
    BenchmarkCase,
    BenchmarkComparison,
    BenchmarkDataset,
    BenchmarkFailureInfo,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkTask,
    FailureCategory,
    OverallQualityScore,
    QualityScore,
    TaskScore,
)


class TestBenchmarkTask:
    def test_enum_values(self):
        assert BenchmarkTask.SUMMARY == "summary"
        assert BenchmarkTask.KEY_TAKEAWAYS == "key_takeaways"
        assert BenchmarkTask.WHY_IT_MATTERS == "why_it_matters"
        assert BenchmarkTask.CATEGORIES == "categories"
        assert BenchmarkTask.COMPANIES == "companies"
        assert BenchmarkTask.TOPICS == "topics"
        assert BenchmarkTask.STRUCTURED_OUTPUT_VALIDITY == "structured_output_validity"


class TestFailureCategory:
    def test_enum_values(self):
        assert FailureCategory.TIMEOUT == "timeout"
        assert FailureCategory.RATE_LIMIT == "rate_limit"
        assert FailureCategory.AUTHENTICATION == "authentication"


class TestQualityScore:
    def test_valid_score(self):
        qs = QualityScore(task=BenchmarkTask.SUMMARY, score=0.8)
        assert qs.score == 0.8
        assert qs.max_score == 1.0

    def test_score_bounded_below(self):
        qs = QualityScore(task=BenchmarkTask.SUMMARY, score=-0.5)
        assert qs.score == 0.0

    def test_score_bounded_above(self):
        qs = QualityScore(task=BenchmarkTask.SUMMARY, score=1.5, max_score=1.0)
        assert qs.score == 1.0

    def test_zero_score(self):
        qs = QualityScore(task=BenchmarkTask.SUMMARY, score=0.0)
        assert qs.score == 0.0


class TestBenchmarkCase:
    def test_valid_case(self):
        case = BenchmarkCase(
            case_id="c1",
            task=BenchmarkTask.SUMMARY,
            article_title="Test",
            article_content="Content here.",
        )
        assert case.case_id == "c1"

    def test_empty_case_id_raises(self):
        with pytest.raises(ValueError):
            BenchmarkCase(
                case_id="",
                task=BenchmarkTask.SUMMARY,
                article_title="Test",
                article_content="Content here.",
            )

    def test_empty_title_raises(self):
        with pytest.raises(ValueError):
            BenchmarkCase(
                case_id="c1",
                task=BenchmarkTask.SUMMARY,
                article_title="",
                article_content="Content here.",
            )

    def test_empty_content_raises(self):
        with pytest.raises(ValueError):
            BenchmarkCase(
                case_id="c1",
                task=BenchmarkTask.SUMMARY,
                article_title="Test",
                article_content="",
            )


class TestTaskScore:
    def test_valid_task_score(self):
        ts = TaskScore(
            task=BenchmarkTask.SUMMARY, cases_evaluated=5, cases_passed=4, cases_failed=1
        )
        assert ts.mean_score == 0.0  # no scores added yet
        assert ts.cases_evaluated == 5

    def test_negative_cases_evaluated_raises(self):
        with pytest.raises(ValueError):
            TaskScore(task=BenchmarkTask.SUMMARY, cases_evaluated=-1)


class TestOverallQualityScore:
    def test_valid_score(self):
        oqs = OverallQualityScore(overall_score=0.7, overall_max=1.0)
        assert oqs.overall_score == 0.7

    def test_negative_score_raises(self):
        with pytest.raises(ValueError):
            OverallQualityScore(overall_score=-0.1, overall_max=1.0)


class TestBenchmarkResult:
    def test_success_result(self):
        result = BenchmarkResult(
            provider_id="openai",
            model="gpt-4",
            case_id="c1",
            task=BenchmarkTask.SUMMARY,
            quality_score=QualityScore(task=BenchmarkTask.SUMMARY, score=0.9),
        )
        assert result.failure is None
        assert result.quality_score.score == 0.9

    def test_failure_result(self):
        failure = BenchmarkFailureInfo(
            provider_id="openai",
            model="gpt-4",
            case_id="c1",
            task=BenchmarkTask.SUMMARY,
            category=FailureCategory.TIMEOUT,
            error_message="timed out",
        )
        result = BenchmarkResult(
            provider_id="openai",
            model="gpt-4",
            case_id="c1",
            task=BenchmarkTask.SUMMARY,
            failure=failure,
        )
        assert result.failure is not None
        assert result.failure.category == FailureCategory.TIMEOUT


class TestBenchmarkRun:
    def test_valid_run(self):
        run = BenchmarkRun(
            run_id="run-1",
            dataset_version="v1",
            benchmark_version="m80-v1",
            started_at=__import__("datetime").datetime.now(UTC),
        )
        assert run.run_id == "run-1"
        assert run.total_requests == 0

    def test_empty_run_id_raises(self):
        with pytest.raises(ValueError):
            BenchmarkRun(
                run_id="",
                dataset_version="v1",
                benchmark_version="m80-v1",
                started_at=__import__("datetime").datetime.now(UTC),
            )


class TestBenchmarkComparison:
    def test_comparison(self):
        comp = BenchmarkComparison(
            provider_id="openai",
            model="gpt-4",
            overall_quality=0.8,
            structured_validity=1.0,
            summary_score=0.7,
            takeaways_score=0.8,
            why_it_matters_score=0.6,
            category_f1=0.9,
            company_f1=0.8,
            topic_f1=0.7,
            success_rate=0.95,
            median_latency_ms=120.0,
            total_input_tokens=1000,
            total_output_tokens=500,
            estimated_cost=0.01,
            cost_known=True,
        )
        assert comp.overall_quality == 0.8
        assert comp.cost_known is True


class TestBenchmarkDataset:
    def test_valid_dataset(self):
        dataset = BenchmarkDataset(name="test", version="v1")
        assert dataset.name == "test"
        assert dataset.cases == ()

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            BenchmarkDataset(name="", version="v1")
