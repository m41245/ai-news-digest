from __future__ import annotations

from uuid import UUID

from celery.utils.log import get_task_logger

from ai_news_digest.application.use_cases.delivery.deliver_digest import (
    DeliverySummary,
)
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.exceptions import ValidationError
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.ports.digest_repository import DigestRepository
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

task_logger = get_task_logger(__name__)
logger = get_logger(__name__)
settings = get_settings()


async def _send_digest_email_impl(digest_id: UUID) -> dict[str, str]:
    """
    Typed implementation function for digest email delivery.
    """
    logger.info(
        "Starting digest email delivery",
        digest_id=str(digest_id),
    )

    async for container in get_container():
        use_case = container.deliver_digest
        summary: DeliverySummary = await use_case.execute(digest_id)

        if summary.has_system_error:
            logger.error(
                "Digest email delivery failed due to system error",
                digest_id=str(digest_id),
                error=summary.system_error,
                sent_count=summary.sent_count,
                failed_count=summary.failed_count,
            )
            raise RuntimeError(summary.system_error)

        logger.info(
            "Digest email delivery completed",
            digest_id=str(digest_id),
            sent_count=summary.sent_count,
            failed_count=summary.failed_count,
            skipped_count=summary.skipped_count,
        )

        return {
            "status": "completed",
            "digest_id": str(digest_id),
            "sent_count": str(summary.sent_count),
            "failed_count": str(summary.failed_count),
            "skipped_count": str(summary.skipped_count),
        }

    return {"status": "not_found"}


async def _send_latest_digest_impl() -> dict[str, str]:
    """
    Typed implementation function for latest digest email delivery.
    """
    logger.info("Starting latest digest email delivery")

    async for container in get_container():
        digest_repository: DigestRepository = container.digest_repository
        recent_digests = await digest_repository.list_recent(limit=1)

        if not recent_digests:
            logger.info("No digests found for email delivery")
            return {"status": "no_digests"}

        latest_digest = recent_digests[0]
        result = await _send_digest_email_impl(latest_digest.id)

        return result

    return {"status": "no_digests"}


@celery_app.task(
    name="workers.tasks.deliver.send_digest_email",
    max_retries=3,
    default_retry_delay=300,
)
async def send_digest_email(digest_id: UUID) -> dict[str, str]:
    """
    Send a digest via email to all configured recipients.

    This task is idempotent: already-sent deliveries are skipped on retry.
    """
    try:
        return await _send_digest_email_impl(digest_id)
    except ValidationError as exc:
        logger.warning(
            "Digest email delivery skipped",
            digest_id=str(digest_id),
            error=str(exc),
        )
        return {
            "status": "skipped",
            "reason": str(exc),
        }
    except Exception as exc:
        logger.error(
            "Digest email delivery failed",
            digest_id=str(digest_id),
            error=str(exc),
            exc_info=True,
        )
        raise


@celery_app.task(
    name="workers.tasks.deliver.send_latest_digest",
    max_retries=3,
    default_retry_delay=300,
)
async def send_latest_digest() -> dict[str, str]:
    """
    Send the most recently generated digest via email.
    """
    try:
        return await _send_latest_digest_impl()
    except ValidationError as exc:
        logger.warning(
            "Latest digest email delivery skipped",
            error=str(exc),
        )
        return {
            "status": "skipped",
            "reason": str(exc),
        }
    except Exception as exc:
        logger.error(
            "Latest digest email delivery failed",
            error=str(exc),
            exc_info=True,
        )
        raise


__all__ = ["send_digest_email", "send_latest_digest"]
