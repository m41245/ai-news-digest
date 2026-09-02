from __future__ import annotations

import time

from ai_news_digest.application.use_cases.article.ingest_all_sources import (
    IngestionSummary,
)
from ai_news_digest.core.logging import get_logger
from ai_news_digest.core.metrics import (
    record_article_collected,
    record_article_deduplicated,
    record_celery_task_duration,
    record_celery_task_failure,
    record_celery_task_success,
    record_rss_ingestion_failure,
    record_rss_ingestion_success,
)
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

logger = get_logger(__name__)

_TASK_NAME = "workers.tasks.ingest.fetch_all_sources"


async def _fetch_all_sources_impl() -> dict[str, int]:
    """
    Typed implementation function for RSS ingestion.

    This function contains the actual business logic and is properly typed for MyPy.
    """
    logger.info("Starting RSS ingestion from all sources")

    async for container in get_container():
        use_case = container.ingest_all_sources
        result: IngestionSummary = await use_case.execute()

        logger.info(
            "RSS ingestion completed successfully",
            sources_processed=result.sources_processed,
            fetched=result.fetched,
            imported=result.imported,
            skipped=result.skipped,
        )

        return {
            "sources_processed": result.sources_processed,
            "fetched": result.fetched,
            "imported": result.imported,
            "skipped": result.skipped,
        }

    # This should never be reached, but MyPy requires a return
    return {"sources_processed": 0, "fetched": 0, "imported": 0, "skipped": 0}


@celery_app.task(
    name="workers.tasks.ingest.fetch_all_sources",
    max_retries=3,
    default_retry_delay=60,
)
async def fetch_all_sources() -> dict[str, int]:
    """
    Fetch articles from all enabled RSS sources.

    This task is idempotent and can be safely retried.
    This is a thin wrapper that calls the typed implementation function.
    """
    start = time.monotonic()
    try:
        result = await _fetch_all_sources_impl()
        record_article_collected(result["fetched"])
        record_article_deduplicated(result["skipped"])
        record_rss_ingestion_success("all_sources")
        await record_celery_task_success(_TASK_NAME)
        return result
    except Exception as exc:
        logger.error(
            "RSS ingestion failed",
            error=str(exc),
            exc_info=True,
        )
        record_rss_ingestion_failure("all_sources")
        await record_celery_task_failure(_TASK_NAME)
        raise
    finally:
        await record_celery_task_duration(_TASK_NAME, time.monotonic() - start)


__all__ = ["fetch_all_sources"]
