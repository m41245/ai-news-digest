"""
Unit tests for ``workers/tasks/quality_gates.py`` (``evaluate_quality_gates``).

``SessionLocal``, its async context-manager behaviour, ``Container``, settings,
the evaluation/health/gate/alert services, drift detection, and Celery task
behaviour are all mocked so no real database or external service is contacted.
Cases that depend on unclear assumptions are asserted against the actual
implementation rather than invented behaviour.
"""

from __future__ import annotations

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_news_digest.domain.evaluation.quality_gates import (
    IntelligenceComponent,
    QualityGateResult,
)
from ai_news_digest.workers.tasks import quality_gates


def _settings(
    *,
    quality_gates_enabled: bool = True,
    quality_gate_evaluation_enabled: bool = True,
    drift_gate_enabled: bool = False,
) -> MagicMock:
    settings = MagicMock()
    settings.quality_gates_enabled = quality_gates_enabled
    settings.quality_gate_evaluation_enabled = quality_gate_evaluation_enabled
    settings.drift_gate_enabled = drift_gate_enabled
    return settings


def _impl_mocks() -> SimpleNamespace:
    """Build and activate all patches for ``_evaluate_quality_gates_impl``.

    Yields a namespace of mocks the test can reconfigure before calling the
    implementation.
    """
    settings = _settings()

    session = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    sessionlocal_mock = MagicMock(return_value=session_cm)

    container = MagicMock()
    container.operational_alert_repository = MagicMock()
    container.quality_gate_repository = MagicMock()
    container.quality_gate_repository.save_result = AsyncMock()
    container.component_health_repository = MagicMock()
    container.component_health_repository.save_snapshot = AsyncMock()
    container.evaluation_repository = MagicMock()
    container.evaluation_repository.get_latest_completed_run = AsyncMock(return_value=None)
    container.evaluation_repository.list_metrics_by_run_id = AsyncMock(return_value=[])
    container_mock = MagicMock(return_value=container)

    report = MagicMock()
    report.status.value = "completed"
    report.error = None
    report.metrics = [MagicMock()]
    report.run_id = "run-1"

    eval_service = MagicMock()
    eval_service.run_evaluation = AsyncMock(return_value=report)

    health = MagicMock(metric_type="extraction_success_rate")
    health_service = MagicMock()
    health_service.build_components_from_gates = MagicMock(return_value=[health])

    gate_service = MagicMock()
    gate_service.default_gates = MagicMock(return_value=[])
    gate_service.evaluate_gates = MagicMock(return_value=[])
    gate_service.build_alert = MagicMock(return_value=None)

    alert_service = MagicMock()
    alert_service.maybe_create_alert = AsyncMock()
    alert_service.resolve_alerts_for_component = AsyncMock()

    drift_detector = MagicMock()
    drift_detector.detect_drift = MagicMock(return_value=[])

    stack = ExitStack()
    stack.enter_context(patch.object(quality_gates, "get_settings", return_value=settings))
    stack.enter_context(
        patch(
            "ai_news_digest.infrastructure.database.session.SessionLocal",
            sessionlocal_mock,
        )
    )
    stack.enter_context(patch("ai_news_digest.bootstrap.container.Container", container_mock))
    stack.enter_context(
        patch(
            "ai_news_digest.application.services.intelligence_evaluation_service.IntelligenceEvaluationService",
            MagicMock(return_value=eval_service),
        )
    )
    stack.enter_context(
        patch(
            "ai_news_digest.application.services.intelligence_health_service.IntelligenceHealthService",
            MagicMock(return_value=health_service),
        )
    )
    stack.enter_context(
        patch(
            "ai_news_digest.application.services.quality_gate_service.QualityGateService",
            MagicMock(return_value=gate_service),
        )
    )
    stack.enter_context(
        patch(
            "ai_news_digest.application.services.operational_alert_service.OperationalAlertService",
            MagicMock(return_value=alert_service),
        )
    )
    stack.enter_context(
        patch.object(quality_gates, "DriftDetector", MagicMock(return_value=drift_detector))
    )

    ns = SimpleNamespace(
        stack=stack,
        settings=settings,
        session=session,
        container=container,
        report=report,
        eval_service=eval_service,
        health_service=health_service,
        gate_service=gate_service,
        alert_service=alert_service,
        drift_detector=drift_detector,
        health=health,
    )
    return ns


async def test_quality_gates_disabled() -> None:
    """Quality gates disabled returns ``skipped`` before opening a session."""
    ns = _impl_mocks()
    try:
        ns.settings.quality_gates_enabled = False
        result = await quality_gates._evaluate_quality_gates_impl()
    finally:
        ns.stack.close()
    assert result == {"status": "skipped", "reason": "quality_gates_disabled"}


async def test_evaluation_report_failed() -> None:
    """A failed evaluation report returns ``skipped`` with reason ``evaluation_failed``."""
    ns = _impl_mocks()
    try:
        ns.report.status.value = "failed"
        ns.report.error = "boom"
        result = await quality_gates._evaluate_quality_gates_impl()
    finally:
        ns.stack.close()
    assert result == {
        "status": "skipped",
        "reason": "evaluation_failed",
        "error": "boom",
    }


async def test_no_gates_configured() -> None:
    """No default gates returns ``skipped`` with reason ``no_gates_configured``."""
    ns = _impl_mocks()
    try:
        ns.gate_service.default_gates.return_value = []
        ns.gate_service.evaluate_gates.return_value = []
        result = await quality_gates._evaluate_quality_gates_impl()
    finally:
        ns.stack.close()
    assert result == {"status": "skipped", "reason": "no_gates_configured"}


async def test_warn_gate_creates_alert() -> None:
    """A warn gate with a built alert creates an operational alert."""
    ns = _impl_mocks()
    try:
        alert = MagicMock(
            severity="warning",
            component=IntelligenceComponent.EXTRACTION,
            gate_id="extraction-success-rate",
            message="m",
            details={},
        )
        ns.gate_service.default_gates.return_value = [MagicMock()]
        gate_result = MagicMock(
            result=QualityGateResult.WARN,
            component=IntelligenceComponent.EXTRACTION,
        )
        ns.gate_service.evaluate_gates.return_value = [gate_result]
        ns.gate_service.build_alert.return_value = alert
        result = await quality_gates._evaluate_quality_gates_impl()
    finally:
        ns.stack.close()
    assert result["status"] == "completed"
    ns.alert_service.maybe_create_alert.assert_awaited_once_with(
        severity=alert.severity,
        component=alert.component,
        gate_id=alert.gate_id,
        message=alert.message,
        details=alert.details,
    )


async def test_warn_gate_no_alert() -> None:
    """A warn gate with no built alert does not create an operational alert."""
    ns = _impl_mocks()
    try:
        ns.gate_service.default_gates.return_value = [MagicMock()]
        gate_result = MagicMock(
            result=QualityGateResult.WARN,
            component=IntelligenceComponent.EXTRACTION,
        )
        ns.gate_service.evaluate_gates.return_value = [gate_result]
        ns.gate_service.build_alert.return_value = None
        await quality_gates._evaluate_quality_gates_impl()
    finally:
        ns.stack.close()
    ns.alert_service.maybe_create_alert.assert_not_awaited()


async def test_fail_gate_creates_alert() -> None:
    """A fail gate with a built alert creates an operational alert."""
    ns = _impl_mocks()
    try:
        alert = MagicMock(
            severity="critical",
            component=IntelligenceComponent.TRENDS,
            gate_id="provenance-completeness",
            message="m",
            details={},
        )
        ns.gate_service.default_gates.return_value = [MagicMock()]
        gate_result = MagicMock(
            result=QualityGateResult.FAIL,
            component=IntelligenceComponent.TRENDS,
        )
        ns.gate_service.evaluate_gates.return_value = [gate_result]
        ns.gate_service.build_alert.return_value = alert
        result = await quality_gates._evaluate_quality_gates_impl()
    finally:
        ns.stack.close()
    assert result["status"] == "completed"
    ns.alert_service.maybe_create_alert.assert_awaited_once_with(
        severity=alert.severity,
        component=alert.component,
        gate_id=alert.gate_id,
        message=alert.message,
        details=alert.details,
    )


async def test_passing_gate_resolves_component_alerts() -> None:
    """A passing gate resolves alerts for its component."""
    ns = _impl_mocks()
    try:
        ns.gate_service.default_gates.return_value = [MagicMock()]
        gate_result = MagicMock(
            result=QualityGateResult.PASS,
            component=IntelligenceComponent.RANKING,
        )
        ns.gate_service.evaluate_gates.return_value = [gate_result]
        result = await quality_gates._evaluate_quality_gates_impl()
    finally:
        ns.stack.close()
    assert result["status"] == "completed"
    ns.alert_service.resolve_alerts_for_component.assert_awaited_once_with(
        component=IntelligenceComponent("ranking")
    )


async def test_drift_disabled() -> None:
    """Drift disabled skips drift detection but still completes and snapshots."""
    ns = _impl_mocks()
    try:
        ns.settings.drift_gate_enabled = False
        ns.gate_service.default_gates.return_value = [MagicMock()]
        gate_result = MagicMock(
            result=QualityGateResult.PASS,
            component=IntelligenceComponent.EXTRACTION,
        )
        ns.gate_service.evaluate_gates.return_value = [gate_result]
        result = await quality_gates._evaluate_quality_gates_impl()
    finally:
        ns.stack.close()
    assert result["status"] == "completed"
    ns.drift_detector.detect_drift.assert_not_called()
    ns.container.component_health_repository.save_snapshot.assert_awaited_once_with(ns.health)


async def test_drift_no_baseline() -> None:
    """Drift enabled with no baseline run skips drift detection."""
    ns = _impl_mocks()
    try:
        ns.settings.drift_gate_enabled = True
        ns.container.evaluation_repository.get_latest_completed_run = AsyncMock(return_value=None)
        ns.gate_service.default_gates.return_value = [MagicMock()]
        gate_result = MagicMock(
            result=QualityGateResult.PASS,
            component=IntelligenceComponent.EXTRACTION,
        )
        ns.gate_service.evaluate_gates.return_value = [gate_result]
        result = await quality_gates._evaluate_quality_gates_impl()
    finally:
        ns.stack.close()
    assert result["status"] == "completed"
    ns.drift_detector.detect_drift.assert_not_called()


async def test_drift_detector_exception() -> None:
    """A drift detector exception is logged and does not fail the task."""
    ns = _impl_mocks()
    try:
        ns.settings.drift_gate_enabled = True
        baseline_run = MagicMock(run_id="baseline-1")
        ns.container.evaluation_repository.get_latest_completed_run = AsyncMock(
            return_value=baseline_run
        )
        ns.container.evaluation_repository.list_metrics_by_run_id = AsyncMock(
            return_value=[MagicMock()]
        )
        ns.drift_detector.detect_drift = MagicMock(side_effect=RuntimeError("drift boom"))
        ns.gate_service.default_gates.return_value = [MagicMock()]
        gate_result = MagicMock(
            result=QualityGateResult.PASS,
            component=IntelligenceComponent.EXTRACTION,
        )
        ns.gate_service.evaluate_gates.return_value = [gate_result]
        result = await quality_gates._evaluate_quality_gates_impl()
    finally:
        ns.stack.close()
    assert result["status"] == "completed"
    ns.drift_detector.detect_drift.assert_called_once()
    ns.container.component_health_repository.save_snapshot.assert_awaited_once_with(ns.health)


async def test_successful_completion() -> None:
    """A successful run returns the completed summary dict."""
    ns = _impl_mocks()
    try:
        ns.gate_service.default_gates.return_value = [MagicMock(), MagicMock()]
        warn_result = MagicMock(
            result=QualityGateResult.WARN,
            component=IntelligenceComponent.EXTRACTION,
        )
        fail_result = MagicMock(
            result=QualityGateResult.FAIL,
            component=IntelligenceComponent.TRENDS,
        )
        ns.gate_service.evaluate_gates.return_value = [warn_result, fail_result]
        result = await quality_gates._evaluate_quality_gates_impl()
    finally:
        ns.stack.close()
    assert result == {
        "status": "completed",
        "run_id": "run-1",
        "gate_count": 2,
        "fail_count": 1,
        "warn_count": 1,
    }


def test_celery_retry_on_error() -> None:
    """An implementation error triggers a Celery retry via ``self.retry``."""
    ns = _impl_mocks()
    try:
        ns.settings.quality_gates_enabled = True
        ns.settings.quality_gate_evaluation_enabled = True
        quality_gates.get_settings.side_effect = RuntimeError("boom")
        retry_mock = MagicMock(side_effect=RuntimeError("retry requested"))
        with (
            patch.object(quality_gates.evaluate_quality_gates, "retry", retry_mock),
            pytest.raises(RuntimeError, match="retry requested"),
        ):
            quality_gates.evaluate_quality_gates(evaluation_type="scheduled", scope="global")
        retry_mock.assert_called_once()
    finally:
        ns.stack.close()
