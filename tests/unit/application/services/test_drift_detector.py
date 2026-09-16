"""Tests for M93 DriftDetector."""

from __future__ import annotations
import pytest
from ai_news_digest.application.services.drift_detector import DriftDetector, DriftState
from ai_news_digest.domain.evaluation.metrics import EvaluationMetricType, MetricValue


class TestDriftDetector:
    def setup_method(self):
        self.detector = DriftDetector()

    def test_detect_no_drift(self):
        baseline = [MetricValue(metric_type=EvaluationMetricType.OVERALL_QUALITY, value=0.8, sample_count=10)]
        current = [MetricValue(metric_type=EvaluationMetricType.OVERALL_QUALITY, value=0.82, sample_count=10)]
        signals = self.detector.detect_drift(baseline, current)
        assert len(signals) == 1
        assert signals[0].state == DriftState.STABLE

    def test_detect_drift(self):
        baseline = [MetricValue(metric_type=EvaluationMetricType.OVERALL_QUALITY, value=0.8, sample_count=10)]
        current = [MetricValue(metric_type=EvaluationMetricType.OVERALL_QUALITY, value=0.5, sample_count=10)]
        signals = self.detector.detect_drift(baseline, current)
        assert signals[0].state == DriftState.DRIFTED

    def test_classify_health_healthy(self):
        metrics = [MetricValue(metric_type=EvaluationMetricType.OVERALL_QUALITY, value=0.8, sample_count=10)]
        status, warnings = self.detector.classify_health([], metrics)
        assert status == "healthy"

    def test_classify_health_degraded(self):
        signals = [
            type("S", (), {"state": DriftState.DRIFTED})()
        ]
        metrics = [MetricValue(metric_type=EvaluationMetricType.OVERALL_QUALITY, value=0.3, sample_count=10)]
        status, warnings = self.detector.classify_health(signals, metrics)
        assert status == "degraded"
