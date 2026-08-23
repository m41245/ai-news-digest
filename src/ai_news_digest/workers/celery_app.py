from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING

from celery import Celery
from celery.app.task import _task_stack

from ai_news_digest.core.config import settings

if TYPE_CHECKING:

    class Task:
        """Celery task base class."""

        abstract: bool

        def run(self, *args: object, **kwargs: object) -> object: ...

        def push_request(self, *args: object, **kwargs: object) -> None: ...

        def pop_request(self) -> None: ...

        def __call__(self, *args: object, **kwargs: object) -> object: ...
else:
    from celery.app.task import Task


class AwaitableTask(Task):
    """Celery task base class that executes coroutine task functions.

    Celery does not natively await coroutine task functions, so this base
    class detects a coroutine returned by ``run`` and runs it to completion
    with :func:`asyncio.run` before the result is stored.

    When an event loop is already running (for example during tests or
    inside certain async frameworks), the coroutine is returned directly
    so the caller can await it.
    """

    abstract = True

    def __call__(self, *args: object, **kwargs: object) -> object:
        _task_stack.push(self)
        self.push_request(args=args, kwargs=kwargs)
        try:
            result = self.run(*args, **kwargs)
            if inspect.iscoroutine(result):
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    return asyncio.run(result)
                return result
            return result
        finally:
            self.pop_request()
            _task_stack.pop()


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
    ],
    task_cls=AwaitableTask,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
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
)

# Load beat schedule so scheduled tasks are registered.
from ai_news_digest.workers.beat_schedule import celery_app as _beat_app  # noqa: E402

if _beat_app is not celery_app:
    raise RuntimeError("Beat schedule must configure the same Celery app.")

__all__ = ["celery_app"]
