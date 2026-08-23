from __future__ import annotations

from celery.utils.log import get_task_logger

from ai_news_digest.application.use_cases.article.ingest_all_sources import (
    IngestionSummary,
)
from ai_news_digest.core.logging import get_logger
from ai_news_digest.workers._container import get_container
from ai_news_digest.workers.celery_app import celery_app

task_logger = get_task_logger(__name__)
logger = get_logger(__name__)


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
    try:
        return await _fetch_all_sources_impl()
    except Exception as exc:
        logger.error(
            "RSS ingestion failed",
            error=str(exc),
            exc_info=True,
        )
        raise


__all__ = ["fetch_all_sources"]
