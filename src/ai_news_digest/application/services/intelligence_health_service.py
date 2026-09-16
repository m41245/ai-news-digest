"""
Intelligence health aggregation for M94.

Aggregates component health, quality gate results, and drift signals
into a deterministic overall health report.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.evaluation.metrics import DriftState, MetricValue
from ai_news_digest.domain.evaluation.quality_gates import (
    ComponentHealth,
    IntelligenceComponent,
    IntelligenceHealthReport,
    IntelligenceHealthStatus,
    QualityGateResult,
    QualityGateResultDetail,
)

logger = get_logger(__name__)

_STATUS_PRECEDENCE = {
    IntelligenceHealthStatus.BLOCKED: 0,
    IntelligenceHealthStatus.DEGRADED: 1,
    IntelligenceHealthStatus.INSUFFICIENT_DATA: 2,
    IntelligenceHealthStatus.UNKNOWN: 3,
    IntelligenceHealthStatus.HEALTHY: 4,
}


class IntelligenceHealthService:
    """Deterministic intelligence health aggregation.

    Aggregates component health and quality gate results into an overall
    health report. Does not modify production behavior.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    def aggregate_component_health(
        self,
        component: IntelligenceComponent,
        gate_results: list[QualityGateResultDetail],
        metric_value: float | None = None,
        metric_type: str | None = None,
        sample_count: int = 0,
        baseline_value: float | None = None,
        drift_state: DriftState | str | None = None,
        evaluation_run_id: str | None = None,
    ) -> ComponentHealth:
        """Aggregate health for a single component from gate results."""
        warnings: list[str] = []

        if not gate_results:
            if sample_count == 0:
                status = IntelligenceHealthStatus.INSUFFICIENT_DATA
                warnings.append("No quality gate results available")
            else:
                status = IntelligenceHealthStatus.UNKNOWN
        else:
            has_fail = any(r.result == QualityGateResult.FAIL for r in gate_results)
            has_warn = any(r.result == QualityGateResult.WARN for r in gate_results)
            has_insufficient = any(
                r.result == QualityGateResult.INSUFFICIENT_DATA for r in gate_results
            )

            if has_fail:
                status = IntelligenceHealthStatus.DEGRADED
                fails = [r.gate_id for r in gate_results if r.result == QualityGateResult.FAIL]
                warnings.append(f"Failed gates: {', '.join(fails)}")
            elif has_warn:
                status = IntelligenceHealthStatus.DEGRADED
                warns = [r.gate_id for r in gate_results if r.result == QualityGateResult.WARN]
                warnings.append(f"Warning gates: {', '.join(warns)}")
            elif has_insufficient and sample_count > 0:
                status = IntelligenceHealthStatus.INSUFFICIENT_DATA
            else:
                status = IntelligenceHealthStatus.HEALTHY

        drift_str = None
        if drift_state is not None:
            drift_str = drift_state.value if hasattr(drift_state, "value") else str(drift_state)
            if drift_str == "drifted" and status == IntelligenceHealthStatus.HEALTHY:
                warnings.append("Metric drifted from baseline")

        return ComponentHealth(
            component=component,
            status=status,
            gate_results=gate_results,
            metric_value=metric_value,
            metric_type=metric_type,
            sample_count=sample_count,
            baseline_value=baseline_value,
            drift_state=drift_str,
            last_evaluation_at=datetime.now(UTC),
            evaluation_run_id=evaluation_run_id,
            warnings=warnings,
        )

    def aggregate_overall_health(
        self,
        components: list[ComponentHealth],
    ) -> IntelligenceHealthReport:
        """Aggregate overall intelligence health from component healths."""
        if not components:
            return IntelligenceHealthReport(
                overall_status=IntelligenceHealthStatus.UNKNOWN,
                components=[],
                generated_at=datetime.now(UTC),
                warnings=["No component health data available"],
            )

        worst_status = IntelligenceHealthStatus.HEALTHY
        all_warnings: list[str] = []

        for component in components:
            if component.warnings:
                all_warnings.extend(component.warnings)
            if _STATUS_PRECEDENCE.get(component.status, 99) < _STATUS_PRECEDENCE.get(
                worst_status, 99
            ):
                worst_status = component.status

        overall = worst_status
        if overall == IntelligenceHealthStatus.HEALTHY and all_warnings:
            overall = IntelligenceHealthStatus.DEGRADED

        return IntelligenceHealthReport(
            overall_status=overall,
            components=components,
            generated_at=datetime.now(UTC),
            warnings=all_warnings,
        )

    def build_components_from_gates(
        self,
        gate_results: list[QualityGateResultDetail],
        metrics: list[MetricValue],
        evaluation_run_id: str | None = None,
    ) -> list[ComponentHealth]:
        """Build component health objects from gate results and metrics."""
        metric_map = {m.metric_type.value: m for m in metrics}
        component_gates: dict[IntelligenceComponent, list[QualityGateResultDetail]] = {}
        for r in gate_results:
            try:
                comp = IntelligenceComponent(r.component)
            except ValueError:
                continue
            component_gates.setdefault(comp, []).append(r)

        components: list[ComponentHealth] = []
        for comp, results in component_gates.items():
            primary_metric = metric_map.get(results[0].metric_type) if results else None
            components.append(
                ComponentHealth(
                    component=comp,
                    status=IntelligenceHealthStatus.UNKNOWN,
                    gate_results=results,
                    metric_value=primary_metric.value if primary_metric else None,
                    metric_type=primary_metric.metric_type.value if primary_metric else None,
                    sample_count=primary_metric.sample_count if primary_metric else 0,
                    evaluation_run_id=evaluation_run_id,
                )
            )

        return components

    def derive_status_from_gates(
        self,
        gate_results: list[QualityGateResultDetail],
    ) -> IntelligenceHealthStatus:
        """Derive component health status from gate results alone."""
        if not gate_results:
            return IntelligenceHealthStatus.INSUFFICIENT_DATA

        has_fail = any(r.result == QualityGateResult.FAIL for r in gate_results)
        has_warn = any(r.result == QualityGateResult.WARN for r in gate_results)
        has_insufficient = any(
            r.result == QualityGateResult.INSUFFICIENT_DATA for r in gate_results
        )

        if has_fail:
            return IntelligenceHealthStatus.DEGRADED
        if has_warn:
            return IntelligenceHealthStatus.DEGRADED
        if has_insufficient:
            return IntelligenceHealthStatus.INSUFFICIENT_DATA
        return IntelligenceHealthStatus.HEALTHY


__all__ = ["IntelligenceHealthService"]
