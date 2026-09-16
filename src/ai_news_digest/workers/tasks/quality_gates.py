"""
Celery task for M94 quality gate evaluation.

Runs bounded quality gate evaluation outside the critical morning pipeline.
"""

from __future__ import annotations

from typing import Any

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.application.services.drift_detector import DriftDetector
from ai_news_digest.domain.evaluation.quality_gates import (
    IntelligenceComponent,
    QualityGateResult,
)
from ai_news_digest.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="workers.tasks.quality_gates.evaluate_quality_gates",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=300,
    time_limit=600,
)
def evaluate_quality_gates(
    self,
    evaluation_type: str = "scheduled",
    scope: str = "global",
) -> dict[str, Any]:
    """Run bounded quality gate evaluation."""
    import asyncio

    from ai_news_digest.application.services.intelligence_evaluation_service import (
        IntelligenceEvaluationService,
    )
    from ai_news_digest.application.services.intelligence_health_service import (
        IntelligenceHealthService,
    )
    from ai_news_digest.application.services.operational_alert_service import (
        OperationalAlertService,
    )
    from ai_news_digest.application.services.quality_gate_service import QualityGateService
    from ai_news_digest.bootstrap.container import Container
    from ai_news_digest.infrastructure.database.session import SessionLocal

    settings = get_settings()
    if not settings.quality_gates_enabled or not settings.quality_gate_evaluation_enabled:
        return {"status": "skipped", "reason": "quality_gates_disabled"}

    async def _run() -> dict[str, Any]:
        async with SessionLocal() as session:
            container = Container(session)
            evaluation_service = IntelligenceEvaluationService()
            health_service = IntelligenceHealthService()
            gate_service = QualityGateService()
            alert_service = OperationalAlertService(
                alert_repository=container.operational_alert_repository,
            )

            report = await evaluation_service.run_evaluation(
                evaluation_type=evaluation_type,
                scope=scope,
                container=container,
            )

            if report.status.value == "failed":
                return {
                    "status": "skipped",
                    "reason": "evaluation_failed",
                    "error": report.error,
                }

            gates = gate_service.default_gates()
            if not gates:
                return {"status": "skipped", "reason": "no_gates_configured"}

            gate_results = gate_service.evaluate_gates(
                gates=gates,
                metrics=report.metrics,
                evaluation_run_id=report.run_id,
            )

            gate_repo = container.quality_gate_repository
            health_repo = container.component_health_repository
            eval_repo = container.evaluation_repository

            for result in gate_results:
                await gate_repo.save_result(result)
                if result.result in ("warn", "fail"):
                    alert = gate_service.build_alert(result)
                    if alert is not None:
                        await alert_service.maybe_create_alert(
                            severity=alert.severity,
                            component=alert.component,
                            gate_id=alert.gate_id,
                            message=alert.message,
                            details=alert.details,
                        )

            component_health = health_service.build_components_from_gates(
                gate_results, report.metrics, report.run_id
            )

            if settings.drift_gate_enabled:
                try:
                    baseline_run = await eval_repo.get_latest_completed_run(
                        scope, report.run_id
                    )
                    if baseline_run is not None:
                        baseline_metrics = await eval_repo.list_metrics_by_run_id(
                            baseline_run.run_id
                        )
                        drift_detector = DriftDetector()
                        drift_signals = drift_detector.detect_drift(
                            baseline_metrics,
                            report.metrics,
                            scope=scope,
                        )
                        component_drift: dict[str, str] = {}
                        for signal in drift_signals:
                            drift_state = (
                                signal.state.value
                                if hasattr(signal.state, "value")
                                else str(signal.state)
                            )
                            component_drift[signal.metric_type] = drift_state

                        for health in component_health:
                            if health.metric_type in component_drift:
                                health.drift_state = component_drift[health.metric_type]
                except Exception as drift_exc:
                    logger.warning(
                        "Drift detection failed",
                        error=str(drift_exc),
                    )

            for health in component_health:
                await health_repo.save_snapshot(health)

            passed_components = {
                r.component.value for r in gate_results if r.result == QualityGateResult.PASS
            }
            all_component_names = {r.component.value for r in gate_results}
            for comp_name in all_component_names:
                if comp_name in passed_components:
                    await alert_service.resolve_alerts_for_component(
                        component=IntelligenceComponent(comp_name),
                    )

            return {
                "status": "completed",
                "run_id": report.run_id,
                "gate_count": len(gate_results),
                "fail_count": sum(1 for r in gate_results if r.result == "fail"),
                "warn_count": sum(1 for r in gate_results if r.result == "warn"),
            }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("Quality gate evaluation task failed", error=str(exc))
        raise self.retry(exc=exc) from exc


__all__ = ["evaluate_quality_gates"]
