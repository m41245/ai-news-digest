"""
Drift detection for M93.

Compares current evaluation metrics against a baseline to detect
material quality changes. Uses bounded deterministic thresholds.
"""

from __future__ import annotations

from ai_news_digest.domain.evaluation.metrics import (
    DriftSignal,
    DriftState,
    EvaluationMetricType,
    MetricValue,
)

_DEFAULT_ABSOLUTE_THRESHOLD = 0.1
_DEFAULT_RELATIVE_THRESHOLD = 0.2
_MIN_SAMPLE_COUNT = 5


class DriftDetector:
    """Bounded deterministic drift detection.

    Compares current metrics against a baseline using configured
    thresholds. Does not use heavyweight statistics.
    """

    def __init__(
        self,
        absolute_threshold: float = _DEFAULT_ABSOLUTE_THRESHOLD,
        relative_threshold: float = _DEFAULT_RELATIVE_THRESHOLD,
        min_sample_count: int = _MIN_SAMPLE_COUNT,
    ) -> None:
        self._absolute_threshold = absolute_threshold
        self._relative_threshold = relative_threshold
        self._min_sample_count = min_sample_count

    def detect_drift(
        self,
        baseline: list[MetricValue],
        current: list[MetricValue],
        scope: str = "",
        provider: str | None = None,
        model: str | None = None,
    ) -> list[DriftSignal]:
        """Detect drift between baseline and current metrics."""
        signals: list[DriftSignal] = []

        current_by_type = {m.metric_type: m for m in current}
        for baseline_metric in baseline:
            current_metric = current_by_type.get(baseline_metric.metric_type)
            if current_metric is None:
                continue

            if (
                baseline_metric.sample_count < self._min_sample_count
                or current_metric.sample_count < self._min_sample_count
            ):
                continue

            difference = current_metric.value - baseline_metric.value
            relative_change = (
                abs(difference) / baseline_metric.value
                if baseline_metric.value != 0
                else (abs(difference) if difference != 0 else 0.0)
            )

            drifted = (
                abs(difference) >= self._absolute_threshold
                and relative_change >= self._relative_threshold
            )
            watch = (
                abs(difference) >= self._absolute_threshold * 0.5
                and not drifted
            )

            state = DriftState.STABLE
            if drifted:
                state = DriftState.DRIFTED
            elif watch:
                state = DriftState.WATCH

            signals.append(DriftSignal(
                metric_type=baseline_metric.metric_type,
                baseline_value=baseline_metric.value,
                current_value=current_metric.value,
                difference=difference,
                relative_change=relative_change,
                baseline_sample_count=baseline_metric.sample_count,
                current_sample_count=current_metric.sample_count,
                threshold=self._absolute_threshold,
                state=state,
                scope=scope,
                provider=provider,
                model=model,
            ))

        return signals

    def classify_health(
        self,
        signals: list[DriftSignal],
        metrics: list[MetricValue],
    ) -> tuple[str, list[str]]:
        """Classify overall health from drift signals and current metrics."""
        warnings: list[str] = []

        drifted = [s for s in signals if s.state == DriftState.DRIFTED]
        watch = [s for s in signals if s.state == DriftState.WATCH]

        if drifted:
            warnings.append(f"{len(drifted)} metric(s) drifted")
        if watch:
            warnings.append(f"{len(watch)} metric(s) in watch state")

        overall = next(
            (m.value for m in metrics if m.metric_type == EvaluationMetricType.OVERALL_QUALITY),
            None,
        )
        if overall is not None and overall < 0.3:
            warnings.append("overall_quality below 0.3")

        if not metrics:
            status = "insufficient_data"
        else:
            status = ("degraded" if drifted else "watch") if drifted or warnings else "healthy"

        return status, warnings


__all__ = ["DriftDetector"]
