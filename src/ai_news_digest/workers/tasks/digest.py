from __future__ import annotations

from datetime import UTC, datetime

from celery.utils.log import get_task_logger

from ai_news_digest.application.use_cases.digest.generate_digest import (
    DigestGenerationResult,
)
from ai_news_digest.core.exceptions import ValidationError
from ai_news_digest.core.logging import get_logger
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

task_logger = get_task_logger(__name__)
logger = get_logger(__name__)


async def _generate_daily_digest_impl() -> dict[str, str]:
    """
    Typed implementation function for daily digest generation.
    """
    logger.info("Starting daily digest generation")

    async for container in get_container():
        use_case = container.generate_digest
        digest_repository = container.digest_repository

        today = datetime.now(UTC)
        title = f"AI News Digest - {today.strftime('%Y-%m-%d')}"

        existing = await digest_repository.get_by_title(title)
        if existing is not None:
            logger.info("Today's digest already exists, skipping generation", title=title)
            return {
                "status": "skipped",
                "reason": "already_generated",
            }

        result: DigestGenerationResult = await use_case.execute(
            title=title,
            limit=50,
        )

        logger.info(
            "Daily digest generation completed",
            digest_id=str(result.digest_id),
            included_articles=result.included_articles,
            generated_at=result.generated_at.isoformat(),
        )

        return {
            "status": "completed",
            "digest_id": str(result.digest_id),
            "included_articles": str(result.included_articles),
            "generated_at": result.generated_at.isoformat(),
        }

    return {"status": "skipped", "reason": "no_eligible_articles"}


@celery_app.task(
    name="workers.tasks.digest.generate_daily_digest",
    max_retries=2,
    default_retry_delay=300,
)
async def generate_daily_digest() -> dict[str, str]:
    """
    Generate a daily digest from categorized articles.

    This task is idempotent and can be safely retried.
    """
    try:
        return await _generate_daily_digest_impl()
    except ValidationError as exc:
        logger.warning(
            "Digest generation skipped - no eligible articles",
            error=str(exc),
        )
        return {
            "status": "skipped",
            "reason": "no_eligible_articles",
        }
    except Exception as exc:
        logger.error(
            "Daily digest generation failed",
            error=str(exc),
            exc_info=True,
        )
        raise


__all__ = ["generate_daily_digest"]
