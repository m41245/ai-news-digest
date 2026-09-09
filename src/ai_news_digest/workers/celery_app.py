from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, Any

import structlog
from celery import Celery
from celery.app.task import _task_stack
from celery.schedules import crontab
from celery.signals import task_postrun, task_prerun, task_retry

from ai_news_digest.core.config import settings
from ai_news_digest.core.metrics import record_celery_task_retry

if TYPE_CHECKING:

    class Task:
        abstract: bool

        def run(self, *args: object, **kwargs: object) -> object: ...

        def push_request(self, *args: object, **kwargs: object) -> None: ...

        def pop_request(self) -> None: ...

        def __call__(self, *args: object, **kwargs: object) -> object: ...
else:
    from celery.app.task import Task


class AwaitableTask(Task):
    abstract = True
    _background_loop: asyncio.AbstractEventLoop | None = None

    def __call__(self, *args: object, **kwargs: object) -> object:
        _task_stack.push(self)
        self.push_request(args=args, kwargs=kwargs)
        try:
            result = self.run(*args, **kwargs)
            if inspect.iscoroutine(result):
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    if self._background_loop is None or self._background_loop.is_closed():
                        self._background_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(self._background_loop)
                    return self._background_loop.run_until_complete(result)
                return result
            return result
        finally:
            self.pop_request()
            _task_stack.pop()


@task_prerun.connect
def bind_task_id_on_start(
    sender: Any = None,
    task_id: str | None = None,
    task: Any = None,
    **kwargs: object,
) -> None:
    structlog.contextvars.bind_contextvars(task_id=task_id)


@task_postrun.connect
def unbind_task_id_on_end(
    sender: Any = None,
    task_id: str | None = None,
    task: Any = None,
    **kwargs: object,
) -> None:
    structlog.contextvars.unbind_contextvars("task_id")


@task_retry.connect
def log_task_retry(
    sender: Any = None,
    task_id: str | None = None,
    exception: BaseException | None = None,
    einfo: Any = None,
    **kwargs: object,
) -> None:
    """Log when a task is being retried, including backoff delay."""
    retries = getattr(sender, "request", None)
    retry_count = retries.retries if retries else 0
    structlog.get_logger().warning(
        "Task retry scheduled",
        task_id=task_id,
        task=sender.name if sender else None,
        retry_count=retry_count,
        exception=str(exception) if exception else None,
    )
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(  # noqa: RUF006
                record_celery_task_retry(str(sender.name) if sender and sender.name else "")
            )
    except RuntimeError:
        pass


celery_app = Celery(
    "ai_news_digest",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "ai_news_digest.workers.tasks.ingest",
        "ai_news_digest.workers.tasks.process",
        "ai_news_digest.workers.tasks.digest",
        "ai_news_digest.workers.tasks.deliver",
        "ai_news_digest.workers.tasks.cleanup",
        "ai_news_digest.workers.tasks.notifications",
    ],
    task_cls=AwaitableTask,
)

_celery_timezone = settings.digest_timezone

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=_celery_timezone,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    task_retry_delay=lambda retries: 60 * (2 ** (retries - 1)),
    worker_cancel_long_running_tasks_on_connection_loss=True,
    worker_shutdown_timeout=30,
    worker_term_timeout=30,
    beat_max_loop_interval=60,
    worker_send_task_events=True,
    task_send_sent_event=True,
    beat_schedule={
        "daily-rss-ingestion": {
            "task": "workers.tasks.ingest.fetch_all_sources",
            "schedule": crontab(hour=6, minute=0),
            "options": {
                "expires": 3600,
                "send_events": True,
            },
        },
        "daily-article-summarization": {
            "task": "workers.tasks.process.summarize_pending_articles",
            "schedule": crontab(hour=6, minute=30),
            "options": {
                "expires": 7200,
                "send_events": True,
            },
        },
        "daily-article-categorization": {
            "task": "workers.tasks.process.categorize_pending_articles",
            "schedule": crontab(hour=7, minute=0),
            "options": {
                "expires": 7200,
                "send_events": True,
            },
        },
        "daily-article-analysis": {
            "task": "workers.tasks.process.analyze_pending_articles",
            "schedule": crontab(hour=7, minute=30),
            "options": {
                "expires": 7200,
                "send_events": True,
            },
        },
        "daily-digest-generation": {
            "task": "workers.tasks.digest.generate_daily_digest",
            "schedule": crontab(
                hour=settings.digest_schedule_hour,
                minute=settings.digest_schedule_minute,
            ),
            "options": {
                "expires": 3600,
                "send_events": True,
            },
        },
        "daily-email-delivery": {
            "task": "workers.tasks.deliver.send_latest_digest",
            "schedule": crontab(hour=8, minute=30),
            "options": {
                "expires": 3600,
                "send_events": True,
            },
        },
        "notification-scheduling": {
            "task": "workers.tasks.notifications.schedule_notifications",
            "schedule": crontab(minute="*/15"),
            "options": {
                "expires": 1800,
                "send_events": True,
            },
        },
        "notification-immediate-delivery": {
            "task": "workers.tasks.notifications.process_immediate_deliveries",
            "schedule": crontab(minute="*/5"),
            "options": {
                "expires": 900,
                "send_events": True,
            },
        },
        "notification-scheduled-delivery": {
            "task": "workers.tasks.notifications.process_scheduled_deliveries",
            "schedule": crontab(minute="*/10"),
            "options": {
                "expires": 1800,
                "send_events": True,
            },
        },
        "notification-retry-failed": {
            "task": "workers.tasks.notifications.retry_failed_deliveries",
            "schedule": crontab(minute="*/30"),
            "options": {
                "expires": 1800,
                "send_events": True,
            },
        },
        "notification-recover-stuck": {
            "task": "workers.tasks.notifications.recover_stuck_deliveries",
            "schedule": crontab(minute="*/15"),
            "options": {
                "expires": 1800,
                "send_events": True,
            },
        },
        "notification-cleanup-deliveries": {
            "task": "workers.tasks.notifications.cleanup_old_notification_deliveries",
            "schedule": crontab(hour=3, minute=0),
            "options": {
                "expires": 3600,
                "send_events": True,
            },
        },
        "notification-cleanup-notifications": {
            "task": "workers.tasks.notifications.cleanup_old_notifications",
            "schedule": crontab(hour=2, minute=0),
            "options": {
                "expires": 3600,
                "send_events": True,
            },
        },
    },
)


__all__ = ["celery_app"]
