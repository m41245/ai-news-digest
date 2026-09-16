"""Tests for M93 evaluation domain models."""

from __future__ import annotations
from datetime import UTC, datetime
import pytest
from ai_news_digest.domain.evaluation.metrics import (
    DriftSignal,
    DriftState,
    EvaluationMetricType,
    EvaluationReport,
    EvaluationStatus,
    MetricValue,
    QualitySnapshot,
)

def test_metric_value_creation():
    m = MetricValue(metric_type=EvaluationMetricType.OVERALL_QUALITY, value=0.8, sample_count=10)
    assert m.value == 0.8
    assert m.sample_count == 10

def test_drift_state_values():
    assert DriftState.STABLE.value == "stable"
    assert DriftState.WATCH.value == "watch"
    assert DriftState.DRIFTED.value == "drifted"

def test_quality_snapshot_creation():
    snap = QualitySnapshot(
        snapshot_id="snap-1",
        evaluated_at=datetime.now(UTC),
        scope="global",
        metrics=[MetricValue(metric_type=EvaluationMetricType.OVERALL_QUALITY, value=0.8, sample_count=10)],
        sample_count=10,
    )
    assert snap.scope == "global"
    assert len(snap.metrics) == 1

def test_evaluation_report_status():
    report = EvaluationReport(
        run_id="run-1",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        status=EvaluationStatus.COMPLETED,
        evaluation_type="daily",
        scope="global",
        dataset_version="production",
        benchmark_version="m93-v1",
        configuration_version="v1",
        metrics=[],
        sample_count=0,
    )
    assert report.status == EvaluationStatus.COMPLETED
