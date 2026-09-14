"""
AI Quality Benchmarking subsystem (M80).

Provides deterministic, provider-neutral quality measurement for AI
provider/model outputs. Consumes existing M79 provider abstractions
and does not modify production routing.
"""

from __future__ import annotations

from ai_news_digest.application.ai.benchmark.evaluator import (
    BenchmarkEvaluator,
    evaluate_benchmark_run,
)
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
from ai_news_digest.application.ai.benchmark.report import (
    BenchmarkReport,
    ComparisonReport,
    generate_benchmark_report,
    generate_comparison_report,
)
from ai_news_digest.application.ai.benchmark.runner import (
    BenchmarkExecutionConfig,
    BenchmarkRunner,
)
from ai_news_digest.application.ai.benchmark.thresholds import (
    QualityThresholds,
    evaluate_thresholds,
)

__all__ = [
    "BenchmarkCase",
    "BenchmarkComparison",
    "BenchmarkDataset",
    "BenchmarkEvaluator",
    "BenchmarkExecutionConfig",
    "BenchmarkFailureInfo",
    "BenchmarkReport",
    "BenchmarkResult",
    "BenchmarkRun",
    "BenchmarkRunner",
    "BenchmarkTask",
    "ComparisonReport",
    "FailureCategory",
    "OverallQualityScore",
    "QualityScore",
    "QualityThresholds",
    "TaskScore",
    "evaluate_benchmark_run",
    "evaluate_thresholds",
    "generate_benchmark_report",
    "generate_comparison_report",
]
