from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.core.metrics import (
    record_celery_task_duration,
    record_celery_task_failure,
    record_celery_task_success,
    record_cleanup_operation,
    record_delivery_attempted,
    record_delivery_failed_permanently,
    record_delivery_recovered,
    record_delivery_succeeded,
    record_notification_created,
    record_notification_evaluation,
)
from ai_news_digest.domain.enums.notification import NotificationSeverity, NotificationType
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

logger = get_logger(__name__)
settings = get_settings()

_BATCH_SIZE = 50

_TASK_NAME_EVALUATE = "workers.tasks.notifications.evaluate_notifications"
_TASK_NAME_EXPIRE = "workers.tasks.notifications.expire_notifications"
_TASK_NAME_SCHEDULE = "workers.tasks.notifications.schedule_notifications"
_TASK_NAME_PROCESS_SCHEDULED = "workers.tasks.notifications.process_scheduled_deliveries"
_TASK_NAME_PROCESS_IMMEDIATE = "workers.tasks.notifications.process_immediate_deliveries"
_TASK_NAME_RETRY_FAILED = "workers.tasks.notifications.retry_failed_deliveries"
_TASK_NAME_RECOVER_STUCK = "workers.tasks.notifications.recover_stuck_deliveries"
_TASK_NAME_CLEANUP_DELIVERIES = "workers.tasks.notifications.cleanup_old_notification_deliveries"
_TASK_NAME_CLEANUP_NOTIFICATIONS = "workers.tasks.notifications.cleanup_old_notifications"


async def _evaluate_notifications_impl(story_id: str) -> dict[str, int]:
    """Evaluate notification eligibility for a story."""
    stats = {"evaluated": 0, "created": 0, "suppressed": 0}
    async for container in get_container():
        engine = container.notification_eligibility_engine
        service = container.notification_service
        story_repo = container.story_cluster_repository
        user_repo = container.user_repository

        story = await story_repo.get_by_id(UUID(story_id))
        if story is None:
            return stats

        users = await user_repo.list_all()
        active_users = [u for u in users if u.is_active]
        for user in active_users:
            stats["evaluated"] += 1
            eligible, _reason, _metadata = await engine.evaluate_story(
                user=user,
                story=story,
                notification_type=NotificationType.IMPORTANT_STORY,
            )
            if eligible:
                await service.create_notification(
                    user=user,
                    notification_type=NotificationType.IMPORTANT_STORY,
                    title=f"Important story: {story.title}",
                    body=story.summary or "A story matching your preferences has been detected.",
                    severity=NotificationSeverity.MEDIUM,
                    story=story,
                )
                stats["created"] += 1
            else:
                stats["suppressed"] += 1
    return stats


@celery_app.task(
    name=_TASK_NAME_EVALUATE,
    max_retries=3,
    default_retry_delay=60,
)
async def evaluate_notifications(story_id: str) -> dict[str, int]:
    """Evaluate notification eligibility for all users for a given story."""
    start = time.monotonic()
    try:
        result = await _evaluate_notifications_impl(story_id)
        await record_celery_task_success(_TASK_NAME_EVALUATE)
        record_notification_evaluation(result.get("evaluated", 0))
        record_notification_created(result.get("created", 0))
        return result
    except Exception as exc:
        logger.error("Notification evaluation failed", story_id=story_id, error=str(exc))
        await record_celery_task_failure(_TASK_NAME_EVALUATE)
        raise
    finally:
        await record_celery_task_duration(_TASK_NAME_EVALUATE, time.monotonic() - start)


@celery_app.task(
    name=_TASK_NAME_EXPIRE,
    max_retries=3,
    default_retry_delay=60,
)
async def expire_old_notifications() -> dict[str, int]:
    """Expire old notifications."""
    start = time.monotonic()
    count = 0
    try:
        async for container in get_container():
            count = await container.notification_repository.expire_old(datetime.now(UTC))
            await record_celery_task_success(_TASK_NAME_EXPIRE)
            return {"expired": count}
    except Exception as exc:
        logger.error("Notification expiry failed", error=str(exc))
        await record_celery_task_failure(_TASK_NAME_EXPIRE)
        raise
    finally:
        await record_celery_task_duration(_TASK_NAME_EXPIRE, time.monotonic() - start)
    return {"expired": count}


async def _schedule_notifications_impl(limit: int = _BATCH_SIZE) -> dict[str, int]:
    async for container in get_container():
        service = container.notification_scheduling_service
        result: dict[str, int] = await service.batch_schedule_pending(limit=limit)
        return result
    return {"scheduled": 0}


@celery_app.task(
    name=_TASK_NAME_SCHEDULE,
    max_retries=3,
    default_retry_delay=60,
)
async def schedule_notifications(limit: int = _BATCH_SIZE) -> dict[str, int]:
    """Batch-schedule pending notifications for delivery."""
    start = time.monotonic()
    try:
        result = await _schedule_notifications_impl(limit=limit)
        await record_celery_task_success(_TASK_NAME_SCHEDULE)
        return result
    except Exception as exc:
        logger.error("Notification scheduling failed", error=str(exc))
        await record_celery_task_failure(_TASK_NAME_SCHEDULE)
        raise
    finally:
        await record_celery_task_duration(_TASK_NAME_SCHEDULE, time.monotonic() - start)


async def _process_scheduled_deliveries_impl(limit: int = _BATCH_SIZE) -> dict[str, int]:
    async for container in get_container():
        service = container.notification_delivery_service
        result: dict[str, int] = await service.process_scheduled_deliveries(limit=limit)
        return result
    return {"processed": 0, "failed": 0}


@celery_app.task(
    name=_TASK_NAME_PROCESS_SCHEDULED,
    max_retries=3,
    default_retry_delay=60,
)
async def process_scheduled_deliveries(limit: int = _BATCH_SIZE) -> dict[str, int]:
    """Process scheduled deliveries that are ready."""
    start = time.monotonic()
    try:
        result = await _process_scheduled_deliveries_impl(limit=limit)
        await record_celery_task_success(_TASK_NAME_PROCESS_SCHEDULED)
        processed = result.get("processed", 0)
        failed = result.get("failed", 0)
        record_delivery_attempted(processed + failed)
        record_delivery_succeeded(processed)
        if failed:
            record_delivery_failed_permanently(failed)
        return result
    except Exception as exc:
        logger.error("Scheduled delivery processing failed", error=str(exc))
        await record_celery_task_failure(_TASK_NAME_PROCESS_SCHEDULED)
        raise
    finally:
        await record_celery_task_duration(_TASK_NAME_PROCESS_SCHEDULED, time.monotonic() - start)


async def _process_immediate_deliveries_impl(limit: int = _BATCH_SIZE) -> dict[str, int]:
    async for container in get_container():
        service = container.notification_delivery_service
        result: dict[str, int] = await service.process_immediate_deliveries(limit=limit)
        return result
    return {"processed": 0, "failed": 0}


@celery_app.task(
    name=_TASK_NAME_PROCESS_IMMEDIATE,
    max_retries=3,
    default_retry_delay=60,
)
async def process_immediate_deliveries(limit: int = _BATCH_SIZE) -> dict[str, int]:
    """Process immediate email delivery records."""
    start = time.monotonic()
    try:
        result = await _process_immediate_deliveries_impl(limit=limit)
        await record_celery_task_success(_TASK_NAME_PROCESS_IMMEDIATE)
        processed = result.get("processed", 0)
        failed = result.get("failed", 0)
        record_delivery_attempted(processed + failed)
        record_delivery_succeeded(processed)
        if failed:
            record_delivery_failed_permanently(failed)
        return result
    except Exception as exc:
        logger.error("Immediate delivery processing failed", error=str(exc))
        await record_celery_task_failure(_TASK_NAME_PROCESS_IMMEDIATE)
        raise
    finally:
        await record_celery_task_duration(_TASK_NAME_PROCESS_IMMEDIATE, time.monotonic() - start)


async def _retry_failed_deliveries_impl(limit: int = _BATCH_SIZE) -> dict[str, int]:
    async for container in get_container():
        service = container.notification_delivery_service
        result: dict[str, int] = await service.retry_failed_deliveries(limit=limit)
        return result
    return {"retried": 0, "failed": 0}


@celery_app.task(
    name=_TASK_NAME_RETRY_FAILED,
    max_retries=3,
    default_retry_delay=60,
)
async def retry_failed_deliveries(limit: int = _BATCH_SIZE) -> dict[str, int]:
    """Retry failed deliveries with exponential backoff."""
    start = time.monotonic()
    try:
        result = await _retry_failed_deliveries_impl(limit=limit)
        await record_celery_task_success(_TASK_NAME_RETRY_FAILED)
        retried = result.get("retried", 0)
        failed = result.get("failed", 0)
        record_delivery_attempted(retried)
        record_delivery_succeeded(retried)
        if failed:
            record_delivery_failed_permanently(failed)
        return result
    except Exception as exc:
        logger.error("Retry failed deliveries failed", error=str(exc))
        await record_celery_task_failure(_TASK_NAME_RETRY_FAILED)
        raise
    finally:
        await record_celery_task_duration(_TASK_NAME_RETRY_FAILED, time.monotonic() - start)


async def _recover_stuck_deliveries_impl(
    timeout_minutes: int = 30,
    limit: int = _BATCH_SIZE,
) -> dict[str, int]:
    async for container in get_container():
        service = container.notification_delivery_service
        result: dict[str, int] = await service.recover_stuck_deliveries(
            timeout_minutes=timeout_minutes,
            limit=limit,
        )
        return result
    return {"recovered": 0}


@celery_app.task(
    name=_TASK_NAME_RECOVER_STUCK,
    max_retries=3,
    default_retry_delay=60,
)
async def recover_stuck_deliveries(
    timeout_minutes: int = 30,
    limit: int = _BATCH_SIZE,
) -> dict[str, int]:
    """Recover deliveries stuck in processing state."""
    start = time.monotonic()
    try:
        result = await _recover_stuck_deliveries_impl(
            timeout_minutes=timeout_minutes,
            limit=limit,
        )
        await record_celery_task_success(_TASK_NAME_RECOVER_STUCK)
        recovered = result.get("recovered", 0)
        record_delivery_recovered(recovered)
        return result
    except Exception as exc:
        logger.error("Stuck delivery recovery failed", error=str(exc))
        await record_celery_task_failure(_TASK_NAME_RECOVER_STUCK)
        raise
    finally:
        await record_celery_task_duration(_TASK_NAME_RECOVER_STUCK, time.monotonic() - start)


async def _cleanup_old_deliveries_impl(days: int = 30) -> dict[str, int]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    deleted = 0
    async for container in get_container():
        delivery_repo = container.notification_delivery_repository
        while True:
            batch = await delivery_repo.list_pending(limit=_BATCH_SIZE)
            to_delete = [d for d in batch if d.created_at is not None and d.created_at < cutoff]
            if not to_delete:
                break
            for delivery in to_delete:
                model = await delivery_repo.get_by_id(delivery.id)
                if model is not None:
                    from sqlalchemy import delete

                    from ai_news_digest.infrastructure.database.models.notification_model import (
                        NotificationDeliveryModel,
                    )

                    await delivery_repo._session.execute(  # type: ignore[attr-defined]
                        delete(NotificationDeliveryModel).where(
                            NotificationDeliveryModel.id == str(delivery.id)
                        )
                    )
                    deleted += 1
            await delivery_repo._commit()  # type: ignore[attr-defined]
            if len(to_delete) < _BATCH_SIZE:
                break
        break
    return {"deleted": deleted, "days": days}


@celery_app.task(
    name=_TASK_NAME_CLEANUP_DELIVERIES,
    max_retries=3,
    default_retry_delay=60,
)
async def cleanup_old_notification_deliveries(days: int = 30) -> dict[str, int]:
    """Clean up old notification delivery records."""
    start = time.monotonic()
    try:
        result = await _cleanup_old_deliveries_impl(days=days)
        await record_celery_task_success(_TASK_NAME_CLEANUP_DELIVERIES)
        record_cleanup_operation(result.get("deleted", 0))
        return result
    except Exception as exc:
        logger.error("Notification delivery cleanup failed", error=str(exc))
        await record_celery_task_failure(_TASK_NAME_CLEANUP_DELIVERIES)
        raise
    finally:
        await record_celery_task_duration(_TASK_NAME_CLEANUP_DELIVERIES, time.monotonic() - start)


@celery_app.task(
    name=_TASK_NAME_CLEANUP_NOTIFICATIONS,
    max_retries=3,
    default_retry_delay=60,
)
async def cleanup_old_notifications(days: int = 90) -> dict[str, int]:
    """Delete notifications and their deliveries older than the specified days."""
    start = time.monotonic()
    try:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        deleted = 0
        async for container in get_container():
            notification_repo = container.notification_repository
            while True:
                old_notifications = await notification_repo.list_old(cutoff, limit=_BATCH_SIZE)
                if not old_notifications:
                    break
                for notification in old_notifications:
                    model = await notification_repo.get_by_id(notification.id)
                    if model is not None:
                        await notification_repo._session.delete(model)  # type: ignore[attr-defined]
                        deleted += 1
                await notification_repo._commit()  # type: ignore[attr-defined]
                if len(old_notifications) < _BATCH_SIZE:
                    break
            break
        await record_celery_task_success(_TASK_NAME_CLEANUP_NOTIFICATIONS)
        record_cleanup_operation(deleted)
        return {"deleted": deleted, "days": days}
    except Exception as exc:
        logger.error("Notification cleanup failed", error=str(exc))
        await record_celery_task_failure(_TASK_NAME_CLEANUP_NOTIFICATIONS)
        raise
    finally:
        await record_celery_task_duration(
            _TASK_NAME_CLEANUP_NOTIFICATIONS,
            time.monotonic() - start,
        )


__all__ = [
    "cleanup_old_notification_deliveries",
    "cleanup_old_notifications",
    "evaluate_notifications",
    "expire_old_notifications",
    "process_immediate_deliveries",
    "process_scheduled_deliveries",
    "recover_stuck_deliveries",
    "retry_failed_deliveries",
    "schedule_notifications",
]
