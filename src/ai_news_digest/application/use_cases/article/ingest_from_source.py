from __future__ import annotations

from dataclasses import dataclass

from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.rss_fetcher import RSSFetcher


@dataclass(slots=True)
class IngestionResult:
    """
    Result of ingesting a single RSS source.
    """

    fetched: int
    imported: int
    skipped: int


class IngestFromSourceUseCase:
    """
    Fetch articles from a single RSS source and persist new ones.
    """

    def __init__(
        self,
        rss_fetcher: RSSFetcher,
        article_repository: ArticleRepository,
    ) -> None:
        self._rss_fetcher = rss_fetcher
        self._article_repository = article_repository

    async def execute(
        self,
        source: Source,
    ) -> IngestionResult:
        """
        Import articles from a single RSS source.
        """

        entries = await self._rss_fetcher.fetch(
            source.feed_url,
        )

        imported = 0
        skipped = 0

        for entry in entries:
            existing = await self._article_repository.get_by_url(
                entry.url,
            )

            if existing is not None:
                skipped += 1
                continue

            article = Article.create(
                title=entry.title,
                url=entry.url,
                summary=entry.summary,
                content=entry.content,
                source_id=source.id,
                published_at=entry.published_at,
            )

            await self._article_repository.create(
                article,
            )

            imported += 1

        return IngestionResult(
            fetched=len(entries),
            imported=imported,
            skipped=skipped,
        )
