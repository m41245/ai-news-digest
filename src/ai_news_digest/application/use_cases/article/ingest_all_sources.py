from __future__ import annotations

from dataclasses import dataclass

from ai_news_digest.application.use_cases.article.ingest_from_source import (
    IngestFromSourceUseCase,
    IngestionResult,
)
from ai_news_digest.domain.ports.source_repository import SourceRepository


@dataclass(slots=True)
class IngestionSummary:
    """
    Summary of ingesting all enabled sources.
    """

    sources_processed: int
    fetched: int
    imported: int
    skipped: int


class IngestAllSourcesUseCase:
    """
    Fetch articles from every enabled source.
    """

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

        fetched = 0
        imported = 0
        skipped = 0

        for source in sources:
            result: IngestionResult = (
                await self._ingest_from_source.execute(source)
            )

            fetched += result.fetched
            imported += result.imported
            skipped += result.skipped

        return IngestionSummary(
            sources_processed=len(sources),
            fetched=fetched,
            imported=imported,
            skipped=skipped,
        )
