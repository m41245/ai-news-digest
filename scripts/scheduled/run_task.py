from __future__ import annotations

import argparse
import asyncio
import sys

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


def _import_impl(task_name: str):
    if task_name == "ingest":
        from ai_news_digest.workers.tasks.ingest import _fetch_all_sources_impl
        return _fetch_all_sources_impl
    if task_name == "summarize":
        from ai_news_digest.workers.tasks.process import _summarize_pending_articles_impl
        return _summarize_pending_articles_impl
    if task_name == "categorize":
        from ai_news_digest.workers.tasks.process import _categorize_pending_articles_impl
        return _categorize_pending_articles_impl
    if task_name == "analyze":
        from ai_news_digest.workers.tasks.process import _analyze_pending_articles_impl
        return _analyze_pending_articles_impl
    if task_name == "digest":
        from ai_news_digest.workers.tasks.digest import _generate_daily_digest_impl
        return _generate_daily_digest_impl
    if task_name == "deliver":
        from ai_news_digest.workers.tasks.deliver import _send_latest_digest_impl
        return _send_latest_digest_impl
    if task_name == "notifications-schedule":
        from ai_news_digest.workers.tasks.notifications import _schedule_notifications_impl
        return _schedule_notifications_impl
    if task_name == "notifications-scheduled":
        from ai_news_digest.workers.tasks.notifications import _process_scheduled_deliveries_impl
        return _process_scheduled_deliveries_impl
    if task_name == "notifications-immediate":
        from ai_news_digest.workers.tasks.notifications import _process_immediate_deliveries_impl
        return _process_immediate_deliveries_impl
    if task_name == "notifications-retry":
        from ai_news_digest.workers.tasks.notifications import _retry_failed_deliveries_impl
        return _retry_failed_deliveries_impl
    if task_name == "notifications-recover":
        from ai_news_digest.workers.tasks.notifications import _recover_stuck_deliveries_impl
        return _recover_stuck_deliveries_impl
    if task_name == "notifications-cleanup-deliveries":
        from ai_news_digest.workers.tasks.notifications import _cleanup_old_deliveries_impl
        return _cleanup_old_deliveries_impl
    if task_name == "notifications-cleanup":
        from ai_news_digest.workers.tasks.notifications import cleanup_old_notifications
        return cleanup_old_notifications
    if task_name == "cleanup-articles":
        from ai_news_digest.workers.tasks.cleanup import cleanup_old_articles
        return cleanup_old_articles
    if task_name == "cleanup-digests":
        from ai_news_digest.workers.tasks.cleanup import cleanup_old_digests
        return cleanup_old_digests
    raise ValueError(f"Unknown task: {task_name}")


async def run_task(task_name: str) -> int:
    impl = _import_impl(task_name)
    try:
        result = await impl()
        logger.info("Task completed", task=task_name, result=result)
        return 0
    except Exception as exc:
        logger.error("Task failed", task=task_name, error=str(exc), exc_info=True)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a scheduled task outside Celery")
    parser.add_argument("task", help="Task name to run")
    args = parser.parse_args()

    settings = get_settings()
    if settings.environment == "production":
        if not settings.redis_url:
            logger.error("REDIS_URL is required in production")
            return 1
        if not settings.celery_broker_url:
            logger.error("CELERY_BROKER_URL is required in production")
            return 1

    return asyncio.run(run_task(args.task))


if __name__ == "__main__":
    sys.exit(main())
