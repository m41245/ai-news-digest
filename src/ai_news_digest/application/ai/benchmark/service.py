"""
Service facade for M80 AI quality benchmarking.

Provides a high-level interface for running benchmarks and generating reports.
"""

from __future__ import annotations

from typing import Any

from ai_news_digest.application.ai.benchmark.models import BenchmarkRun
from ai_news_digest.application.ai.benchmark.report import (
    BenchmarkReport,
    ComparisonReport,
    generate_benchmark_report,
    generate_comparison_report,
)
from ai_news_digest.application.ai.benchmark.runner import BenchmarkExecutionConfig, BenchmarkRunner
from ai_news_digest.application.ai.benchmark.thresholds import (
    QualityThresholds,
    evaluate_thresholds,
)


class BenchmarkService:
    """Facade for benchmark operations."""

    def __init__(
        self,
        provider_manager: Any,
        registry: Any,
        config: BenchmarkExecutionConfig | None = None,
    ) -> None:
        self._runner = BenchmarkRunner(provider_manager, registry, config)

    async def run_benchmark(self) -> BenchmarkRun:
        """Execute a benchmark run."""
        return await self._runner.run()

    def generate_report(self, run: BenchmarkRun) -> BenchmarkReport:
        """Generate a machine-readable benchmark report."""
        return generate_benchmark_report(run)

    def generate_comparison(self, run: BenchmarkRun) -> ComparisonReport:
        """Generate a deterministic provider comparison report."""
        return generate_comparison_report(run)

    def evaluate_thresholds(
        self,
        run: BenchmarkRun,
        thresholds: QualityThresholds | None = None,
    ) -> Any:
        """Evaluate a run against quality thresholds."""
        return evaluate_thresholds(run, thresholds)


__all__ = ["BenchmarkService"]
