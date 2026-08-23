from __future__ import annotations

import logging
from dataclasses import dataclass

from ai_news_digest.application.use_cases.article.ingest_from_source import (
    IngestFromSourceUseCase,
)
from ai_news_digest.domain.ports.source_repository import SourceRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IngestionSummary:
    """Summary of ingesting all enabled sources."""

    sources_processed: int = 0
    sources_failed: int = 0
    fetched: int = 0
    imported: int = 0
    skipped: int = 0
    failed: int = 0


class IngestAllSourcesUseCase:
    """Fetch articles from every enabled source, continuing past failures."""

    def __init__(
        self,
        source_repository: SourceRepository,
        ingest_from_source: IngestFromSourceUseCase,
    ) -> None:
        self._source_repository = source_repository
        self._ingest_from_source = ingest_from_source

    async def execute(
        self,
    ) -> IngestionSummary:
        sources = await self._source_repository.list_enabled()

        summary = IngestionSummary()

        if not sources:
            return summary

        for source in sources:
            try:
                result = await self._ingest_from_source.execute(source)
            except Exception:
                summary.sources_failed += 1
                logger.exception("Failed to ingest source '%s'.", source.name)
                continue

            summary.sources_processed += 1
            summary.fetched += result.fetched
            summary.imported += result.imported
            summary.skipped += result.skipped
            summary.failed += result.failed

        return summary
