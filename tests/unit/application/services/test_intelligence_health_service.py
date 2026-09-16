"""Tests for M94 intelligence health aggregation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_news_digest.application.services.intelligence_health_service import (
    IntelligenceHealthService,
)
from ai_news_digest.domain.evaluation.quality_gates import (
    AlertSeverity,
    ComponentHealth,
    GateOperator,
    IntelligenceComponent,
    IntelligenceHealthStatus,
    QualityGateResult,
    QualityGateResultDetail,
)


def _make_gate_result(
    gate_id: str,
    component: IntelligenceComponent,
    result: QualityGateResult,
) -> QualityGateResultDetail:
    return QualityGateResultDetail(
        gate_id=gate_id,
        component=component,
        metric_type="test_metric",
        result=result,
        current_value=0.5,
        threshold=0.7,
        operator=GateOperator.GTE,
        sample_count=10,
        min_sample_size=5,
        severity=AlertSeverity.WARNING,
        explanation=f"Test {result.value}",
        evaluated_at=datetime.now(UTC),
    )


class TestIntelligenceHealthService:
    @pytest.fixture
    def service(self) -> IntelligenceHealthService:
        return IntelligenceHealthService()

    def test_aggregate_overall_health_empty(self, service: IntelligenceHealthService) -> None:
        report = service.aggregate_overall_health([])
        assert report.overall_status == IntelligenceHealthStatus.UNKNOWN
        assert "No component health data" in report.warnings[0]

    def test_aggregate_overall_health_all_healthy(self, service: IntelligenceHealthService) -> None:
        components = [
            ComponentHealth(
                component=IntelligenceComponent.EXTRACTION,
                status=IntelligenceHealthStatus.HEALTHY,
            ),
            ComponentHealth(
                component=IntelligenceComponent.ARTICLE_ANALYSIS,
                status=IntelligenceHealthStatus.HEALTHY,
            ),
        ]
        report = service.aggregate_overall_health(components)
        assert report.overall_status == IntelligenceHealthStatus.HEALTHY

    def test_aggregate_overall_health_one_degraded(
        self, service: IntelligenceHealthService
    ) -> None:
        components = [
            ComponentHealth(
                component=IntelligenceComponent.EXTRACTION,
                status=IntelligenceHealthStatus.HEALTHY,
            ),
            ComponentHealth(
                component=IntelligenceComponent.ARTICLE_ANALYSIS,
                status=IntelligenceHealthStatus.DEGRADED,
                warnings=["Failed gate: structured-output-validity"],
            ),
        ]
        report = service.aggregate_overall_health(components)
        assert report.overall_status == IntelligenceHealthStatus.DEGRADED
        assert "Failed gate: structured-output-validity" in report.warnings

    def test_aggregate_overall_health_blocked_overrides_degraded(
        self, service: IntelligenceHealthService
    ) -> None:
        components = [
            ComponentHealth(
                component=IntelligenceComponent.EXTRACTION,
                status=IntelligenceHealthStatus.BLOCKED,
            ),
            ComponentHealth(
                component=IntelligenceComponent.ARTICLE_ANALYSIS,
                status=IntelligenceHealthStatus.DEGRADED,
            ),
        ]
        report = service.aggregate_overall_health(components)
        assert report.overall_status == IntelligenceHealthStatus.BLOCKED

    def test_aggregate_component_health_no_gates(self, service: IntelligenceHealthService) -> None:
        health = service.aggregate_component_health(
            component=IntelligenceComponent.EXTRACTION,
            gate_results=[],
            sample_count=0,
        )
        assert health.status == IntelligenceHealthStatus.INSUFFICIENT_DATA

    def test_aggregate_component_health_with_fail(self, service: IntelligenceHealthService) -> None:
        gate_results = [
            _make_gate_result(
                "extraction-success-rate",
                IntelligenceComponent.EXTRACTION,
                QualityGateResult.FAIL,
            )
        ]
        health = service.aggregate_component_health(
            component=IntelligenceComponent.EXTRACTION,
            gate_results=gate_results,
            sample_count=10,
        )
        assert health.status == IntelligenceHealthStatus.DEGRADED
        assert "Failed gates: extraction-success-rate" in health.warnings

    def test_aggregate_component_health_with_warn(self, service: IntelligenceHealthService) -> None:
        gate_results = [
            _make_gate_result(
                "extraction-success-rate",
                IntelligenceComponent.EXTRACTION,
                QualityGateResult.WARN,
            )
        ]
        health = service.aggregate_component_health(
            component=IntelligenceComponent.EXTRACTION,
            gate_results=gate_results,
            sample_count=10,
        )
        assert health.status == IntelligenceHealthStatus.DEGRADED

    def test_derive_status_from_gates(self, service: IntelligenceHealthService) -> None:
        assert (
            service.derive_status_from_gates([])
            == IntelligenceHealthStatus.INSUFFICIENT_DATA
        )
        gate_fail = _make_gate_result(
            "g1", IntelligenceComponent.EXTRACTION, QualityGateResult.FAIL
        )
        assert service.derive_status_from_gates([gate_fail]) == IntelligenceHealthStatus.DEGRADED
        gate_warn = _make_gate_result(
            "g2", IntelligenceComponent.EXTRACTION, QualityGateResult.WARN
        )
        assert service.derive_status_from_gates([gate_warn]) == IntelligenceHealthStatus.DEGRADED
        gate_pass = _make_gate_result(
            "g3", IntelligenceComponent.EXTRACTION, QualityGateResult.PASS
        )
        assert service.derive_status_from_gates([gate_pass]) == IntelligenceHealthStatus.HEALTHY


__all__ = ["TestIntelligenceHealthService"]
