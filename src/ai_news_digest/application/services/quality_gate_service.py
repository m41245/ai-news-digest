"""
Quality gate evaluation for M94.

Provides deterministic evaluation of quality gates over M93 metrics.
Does not modify production algorithms.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.evaluation.metrics import EvaluationMetricType, MetricValue
from ai_news_digest.domain.evaluation.quality_gates import (
    AlertSeverity,
    GateOperator,
    IntelligenceComponent,
    OperationalAlert,
    QualityGate,
    QualityGateResult,
    QualityGateResultDetail,
)

logger = get_logger(__name__)


def _evaluate_operator(
    operator: GateOperator,
    value: float,
    threshold: float,
) -> bool:
    if operator == GateOperator.GT:
        return value > threshold
    if operator == GateOperator.GTE:
        return value >= threshold
    if operator == GateOperator.LT:
        return value < threshold
    if operator == GateOperator.LTE:
        return value <= threshold
    if operator == GateOperator.EQ:
        return value == threshold
    if operator == GateOperator.NEQ:
        return value != threshold
    raise ValueError(f"Unsupported operator: {operator}")


def _build_explanation(
    gate: QualityGate,
    current_value: float | None,
    sample_count: int,
    result: str,
) -> str:
    value_str = f"{current_value:.3f}" if current_value is not None else "N/A"
    threshold_str = f"{gate.threshold:.3f}"
    return (
        f"{gate.metric_type} = {value_str} "
        f"(threshold {gate.operator.value} {threshold_str}, "
        f"samples={sample_count}) -> {result.upper()}"
    )


class QualityGateService:
    """Deterministic quality gate evaluation.

    Evaluates configured quality gates against current metrics.
    Does not modify production behavior.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    def default_gates(self) -> list[QualityGate]:
        """Return the default quality gates based on configuration."""
        if not self._settings.quality_gates_enabled:
            return []

        gates: list[QualityGate] = [
            QualityGate(
                gate_id="extraction-success-rate",
                component=IntelligenceComponent.EXTRACTION,
                metric_type=EvaluationMetricType.EXTRACTION_SUCCESS_RATE.value,
                operator=GateOperator.GTE,
                threshold=self._settings.extraction_success_threshold,
                min_sample_size=self._settings.minimum_evaluation_samples,
                severity=AlertSeverity.WARNING,
                description="Minimum extraction success rate",
                version="v1",
            ),
            QualityGate(
                gate_id="structured-output-validity",
                component=IntelligenceComponent.ARTICLE_ANALYSIS,
                metric_type=EvaluationMetricType.STRUCTURED_OUTPUT_VALIDITY.value,
                operator=GateOperator.GTE,
                threshold=self._settings.structured_validity_threshold,
                min_sample_size=self._settings.minimum_evaluation_samples,
                severity=AlertSeverity.WARNING,
                description="Minimum structured output validity rate",
                version="v1",
            ),
            QualityGate(
                gate_id="provenance-completeness",
                component=IntelligenceComponent.ARTICLE_ANALYSIS,
                metric_type=EvaluationMetricType.PROVENANCE_COMPLETENESS.value,
                operator=GateOperator.GTE,
                threshold=self._settings.provenance_completeness_threshold,
                min_sample_size=self._settings.minimum_evaluation_samples,
                severity=AlertSeverity.WARNING,
                description="Minimum provenance completeness rate",
                version="v1",
            ),
            QualityGate(
                gate_id="evidence-attachment-rate",
                component=IntelligenceComponent.CLAIMS_EVIDENCE,
                metric_type=EvaluationMetricType.EVIDENCE_ATTACHMENT_RATE.value,
                operator=GateOperator.GTE,
                threshold=self._settings.evidence_coverage_threshold,
                min_sample_size=self._settings.minimum_evaluation_samples,
                severity=AlertSeverity.WARNING,
                description="Minimum evidence attachment rate",
                version="v1",
            ),
        ]
        return gates

    def evaluate_gate(
        self,
        gate: QualityGate,
        metrics: list[MetricValue],
        evaluation_run_id: str | None = None,
    ) -> QualityGateResultDetail:
        """Evaluate a single quality gate against current metrics."""
        metric_map = {m.metric_type.value: m for m in metrics}
        metric = metric_map.get(gate.metric_type)

        now = datetime.now(UTC)

        if metric is None:
            return QualityGateResultDetail(
                gate_id=gate.gate_id,
                component=gate.component,
                metric_type=gate.metric_type,
                result=QualityGateResult.INSUFFICIENT_DATA,
                current_value=None,
                threshold=gate.threshold,
                operator=gate.operator,
                sample_count=0,
                min_sample_size=gate.min_sample_size,
                severity=gate.severity,
                explanation=f"Metric {gate.metric_type} not found in current evaluation",
                evaluated_at=now,
                evaluation_run_id=evaluation_run_id,
                configuration_version=gate.version,
            )

        if metric.sample_count < gate.min_sample_size:
            return QualityGateResultDetail(
                gate_id=gate.gate_id,
                component=gate.component,
                metric_type=gate.metric_type,
                result=QualityGateResult.INSUFFICIENT_DATA,
                current_value=metric.value,
                threshold=gate.threshold,
                operator=gate.operator,
                sample_count=metric.sample_count,
                min_sample_size=gate.min_sample_size,
                severity=gate.severity,
                explanation=(
                    f"Insufficient samples: {metric.sample_count} < {gate.min_sample_size}"
                ),
                evaluated_at=now,
                evaluation_run_id=evaluation_run_id,
                configuration_version=gate.version,
            )

        passed = _evaluate_operator(gate.operator, metric.value, gate.threshold)
        result = QualityGateResult.PASS if passed else QualityGateResult.FAIL

        explanation = _build_explanation(gate, metric.value, metric.sample_count, result.value)

        return QualityGateResultDetail(
            gate_id=gate.gate_id,
            component=gate.component,
            metric_type=gate.metric_type,
            result=result,
            current_value=metric.value,
            threshold=gate.threshold,
            operator=gate.operator,
            sample_count=metric.sample_count,
            min_sample_size=gate.min_sample_size,
            severity=gate.severity,
            explanation=explanation,
            evaluated_at=now,
            evaluation_run_id=evaluation_run_id,
            configuration_version=gate.version,
        )

    def evaluate_gates(
        self,
        gates: list[QualityGate],
        metrics: list[MetricValue],
        evaluation_run_id: str | None = None,
    ) -> list[QualityGateResultDetail]:
        """Evaluate all quality gates against current metrics."""
        results: list[QualityGateResultDetail] = []
        for gate in gates:
            if not gate.enabled:
                continue
            results.append(self.evaluate_gate(gate, metrics, evaluation_run_id))
        return results

    def build_alert(
        self,
        gate_result: QualityGateResultDetail,
        deduplication_window_seconds: int = 3600,
    ) -> OperationalAlert | None:
        """Build an operational alert from a failed/warned quality gate result."""
        if gate_result.result in (
            QualityGateResult.PASS,
            QualityGateResult.INSUFFICIENT_DATA,
        ):
            return None

        severity = gate_result.severity
        if gate_result.result == QualityGateResult.WARN:
            severity = AlertSeverity.WARNING
        elif gate_result.result == QualityGateResult.FAIL:
            severity = AlertSeverity.CRITICAL

        now = datetime.now(UTC)
        time_window = now.strftime("%Y%m%d%H")
        dedup_key = (
            f"m94:{gate_result.component.value}:{gate_result.gate_id}:{time_window}"
        )

        return OperationalAlert(
            alert_id=f"alert-{gate_result.gate_id}-{now.strftime('%Y%m%dT%H%M%SZ')}",
            severity=severity,
            component=gate_result.component,
            gate_id=gate_result.gate_id,
            message=gate_result.explanation,
            details={
                "current_value": gate_result.current_value,
                "threshold": gate_result.threshold,
                "operator": gate_result.operator.value,
                "sample_count": gate_result.sample_count,
                "result": gate_result.result.value,
            },
            resolved=False,
            created_at=now,
            deduplication_key=dedup_key,
        )


__all__ = ["QualityGateService"]
