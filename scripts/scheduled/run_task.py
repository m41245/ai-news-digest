import argparse
import asyncio
import sys

from ai_news_digest.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


def _import_impl(task_name: str):
    if task_name == "ingest":
        from ai_news_digest.workers.tasks.ingest import _fetch_all_sources_impl
        return _fetch_all_sources_impl
    if task_name == "summarize":
        from ai_news_digest.workers.tasks.process import _summarize_pending_articles_impl
        return lambda: _summarize_pending_articles_impl(execute_directly=True)
    if task_name == "categorize":
        from ai_news_digest.workers.tasks.process import _categorize_pending_articles_impl
        return lambda: _categorize_pending_articles_impl(execute_directly=True)
    if task_name == "analyze":
        from ai_news_digest.workers.tasks.process import _analyze_pending_articles_impl
        return lambda: _analyze_pending_articles_impl(execute_directly=True)
    if task_name == "cluster":
        from ai_news_digest.workers.tasks.cluster import _cluster_pending_articles_impl
        return lambda: _cluster_pending_articles_impl(execute_directly=True)
    if task_name == "timeline":
        from ai_news_digest.workers.tasks.timeline import _generate_timeline_impl
        return _generate_timeline_impl
    if task_name == "ranking":
        from ai_news_digest.workers.tasks.ranking import _rank_stories_impl
        return _rank_stories_impl
    if task_name == "conflict":
        from ai_news_digest.workers.tasks.conflict import _detect_claim_conflicts_impl
        return _detect_claim_conflicts_impl
    if task_name == "story-activity":
        from ai_news_digest.workers.tasks.story_activity import _detect_story_activity_impl
        return _detect_story_activity_impl
    if task_name == "trend":
        from ai_news_digest.workers.tasks.trend import _detect_trends_impl
        return _detect_trends_impl
    if task_name == "evaluation":
        from ai_news_digest.workers.tasks.evaluation import _run_intelligence_evaluation_impl
        return _run_intelligence_evaluation_impl
    if task_name == "quality-gates":
        from ai_news_digest.workers.tasks.quality_gates import _evaluate_quality_gates_impl
        return _evaluate_quality_gates_impl
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
    try:
        impl = _import_impl(task_name)
    except ValueError as exc:
        logger.error("Task failed", task=task_name, error=str(exc), exc_info=True)
        return 1
    try:
        result = impl()
        if hasattr(result, "__await__"):
            result = await result
        logger.info("Task completed", task=task_name, result=result)
        return 0
    except Exception as exc:
        logger.error("Task failed", task=task_name, error=str(exc), exc_info=True)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a scheduled task outside Celery")
    parser.add_argument("task", help="Task name to run")
    args = parser.parse_args()

    return asyncio.run(run_task(args.task))


if __name__ == "__main__":
    sys.exit(main())
