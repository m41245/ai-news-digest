"""Tests for M94 quality gate evaluation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ai_news_digest.application.services.quality_gate_service import QualityGateService
from ai_news_digest.domain.evaluation.metrics import EvaluationMetricType, MetricValue
from ai_news_digest.domain.evaluation.quality_gates import (
    AlertSeverity,
    GateOperator,
    IntelligenceComponent,
    QualityGate,
    QualityGateResult,
)


def _make_metric(metric_type: str, value: float, sample_count: int = 10) -> MetricValue:
    return MetricValue(
        metric_type=EvaluationMetricType(metric_type),
        value=value,
        sample_count=sample_count,
    )


class TestQualityGateService:
    @pytest.fixture
    def service(self, monkeypatch: pytest.MonkeyPatch) -> QualityGateService:
        monkeypatch.setattr(
            "ai_news_digest.application.services.quality_gate_service.get_settings",
            lambda: MagicMock(
                quality_gates_enabled=True,
                extraction_success_threshold=0.7,
                structured_validity_threshold=0.8,
                provenance_completeness_threshold=0.8,
                evidence_coverage_threshold=0.5,
                minimum_evaluation_samples=5,
            ),
        )
        return QualityGateService()

    def test_default_gates_returns_gates_when_enabled(self, service: QualityGateService) -> None:
        gates = service.default_gates()
        assert len(gates) > 0
        gate_ids = [g.gate_id for g in gates]
        assert "extraction-success-rate" in gate_ids
        assert "structured-output-validity" in gate_ids
        assert "provenance-completeness" in gate_ids
        assert "evidence-attachment-rate" in gate_ids

    def test_default_gates_empty_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "ai_news_digest.application.services.quality_gate_service.get_settings",
            lambda: MagicMock(quality_gates_enabled=False),
        )
        service = QualityGateService()
        assert service.default_gates() == []

    def test_evaluate_gate_pass(self, service: QualityGateService) -> None:
        gate = QualityGate(
            gate_id="test-gate",
            component=IntelligenceComponent.EXTRACTION,
            metric_type=EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value,
            operator=GateOperator.GTE,
            threshold=0.7,
            min_sample_size=5,
        )
        metrics = [_make_metric(EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value, 0.9, 10)]
        result = service.evaluate_gate(gate, metrics)
        assert result.result == QualityGateResult.PASS
        assert result.current_value == 0.9
        assert result.sample_count == 10

    def test_evaluate_gate_fail(self, service: QualityGateService) -> None:
        gate = QualityGate(
            gate_id="test-gate",
            component=IntelligenceComponent.EXTRACTION,
            metric_type=EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value,
            operator=GateOperator.GTE,
            threshold=0.7,
            min_sample_size=5,
        )
        metrics = [_make_metric(EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value, 0.5, 10)]
        result = service.evaluate_gate(gate, metrics)
        assert result.result == QualityGateResult.FAIL
        assert result.current_value == 0.5

    def test_evaluate_gate_insufficient_data_missing_metric(
        self, service: QualityGateService
    ) -> None:
        gate = QualityGate(
            gate_id="test-gate",
            component=IntelligenceComponent.EXTRACTION,
            metric_type=EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value,
            operator=GateOperator.GTE,
            threshold=0.7,
            min_sample_size=5,
        )
        metrics = [_make_metric(EvaluationMetricType.STRUCTURED_OUTPUT_VALIDITY.value, 0.9, 10)]
        result = service.evaluate_gate(gate, metrics)
        assert result.result == QualityGateResult.INSUFFICIENT_DATA
        assert result.sample_count == 0

    def test_evaluate_gate_insufficient_data_low_sample_count(
        self, service: QualityGateService
    ) -> None:
        gate = QualityGate(
            gate_id="test-gate",
            component=IntelligenceComponent.EXTRACTION,
            metric_type=EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value,
            operator=GateOperator.GTE,
            threshold=0.7,
            min_sample_size=10,
        )
        metrics = [_make_metric(EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value, 0.9, 3)]
        result = service.evaluate_gate(gate, metrics)
        assert result.result == QualityGateResult.INSUFFICIENT_DATA
        assert result.sample_count == 3

    def test_evaluate_gates_runs_all_enabled(self, service: QualityGateService) -> None:
        gates = service.default_gates()
        metrics = [
            _make_metric(EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value, 0.9, 10),
            _make_metric(EvaluationMetricType.STRUCTURED_OUTPUT_VALIDITY.value, 0.9, 10),
            _make_metric(EvaluationMetricType.PROVENANCE_COMPLETENESS.value, 0.9, 10),
            _make_metric(EvaluationMetricType.EVIDENCE_ATTACHMENT_RATE.value, 0.9, 10),
        ]
        results = service.evaluate_gates(gates, metrics)
        assert len(results) == len(gates)
        assert all(r.result == QualityGateResult.PASS for r in results)

    def test_build_alert_for_fail(self, service: QualityGateService) -> None:
        gate = QualityGate(
            gate_id="test-gate",
            component=IntelligenceComponent.EXTRACTION,
            metric_type=EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value,
            operator=GateOperator.GTE,
            threshold=0.7,
            min_sample_size=5,
            severity=AlertSeverity.CRITICAL,
        )
        metrics = [_make_metric(EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value, 0.5, 10)]
        result = service.evaluate_gate(gate, metrics)
        alert = service.build_alert(result)
        assert alert is not None
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.component == IntelligenceComponent.EXTRACTION
        assert alert.gate_id == "test-gate"

    def test_build_alert_returns_none_for_pass(self, service: QualityGateService) -> None:
        gate = QualityGate(
            gate_id="test-gate",
            component=IntelligenceComponent.EXTRACTION,
            metric_type=EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value,
            operator=GateOperator.GTE,
            threshold=0.7,
            min_sample_size=5,
        )
        metrics = [_make_metric(EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value, 0.9, 10)]
        result = service.evaluate_gate(gate, metrics)
        alert = service.build_alert(result)
        assert alert is None


__all__ = ["TestQualityGateService"]
