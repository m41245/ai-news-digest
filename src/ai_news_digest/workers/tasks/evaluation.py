"""
Celery task for M93 intelligence evaluation.

Runs bounded intelligence evaluation outside the critical morning pipeline.
"""

from __future__ import annotations

from typing import Any

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(
    name="workers.tasks.evaluation.run_intelligence_evaluation",
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    soft_time_limit=600,
    time_limit=900,
)
def run_intelligence_evaluation(
    self,
    evaluation_type: str = "scheduled",
    scope: str = "global",
) -> dict[str, Any]:
    """Run bounded intelligence evaluation."""
    import asyncio

    from ai_news_digest.application.services.intelligence_evaluation_service import (
        IntelligenceEvaluationService,
    )
    from ai_news_digest.bootstrap.container import Container
    from ai_news_digest.infrastructure.database.session import SessionLocal

    settings = get_settings()
    if not settings.evaluation_enabled:
        return {"status": "skipped", "reason": "evaluation_disabled"}

    async def _run() -> dict[str, Any]:
        async with SessionLocal() as session:
            container = Container(session)
            service = IntelligenceEvaluationService()
            report = await service.run_evaluation(
                evaluation_type=evaluation_type,
                scope=scope,
                container=container,
            )

            if report.status.value != "failed":
                try:
                    repo = container.evaluation_repository
                    await repo.save_run(report)
                    await repo.save_metrics(report.run_id, report.metrics)
                    snapshot = service.create_snapshot(report)
                    await repo.save_snapshot(snapshot)
                except Exception as persist_exc:
                    logger.warning("Failed to persist evaluation", error=str(persist_exc))

            return {
                "run_id": report.run_id,
                "status": report.status.value,
                "sample_count": report.sample_count,
                "metric_count": len(report.metrics),
                "error": report.error,
            }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("Evaluation task failed", error=str(exc))
        raise self.retry(exc=exc) from exc


__all__ = ["run_intelligence_evaluation"]
