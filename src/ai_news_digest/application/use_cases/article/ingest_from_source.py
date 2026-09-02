from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.rss_entry import RssEntry
from ai_news_digest.domain.models.source import Source
from ai_news_digest.domain.models.url import CanonicalUrl
from ai_news_digest.domain.ports.article_repository import ArticleRepository
from ai_news_digest.domain.ports.rss_fetcher import RSSFetcher


@dataclass(slots=True)
class IngestionResult:
    """Result of ingesting a single RSS source."""

    fetched: int
    imported: int
    skipped: int
    failed: int = 0


class IngestFromSourceUseCase:
    """Fetch articles from a single RSS source and persist new ones."""

    def __init__(
        self,
        rss_fetcher: RSSFetcher,
        article_repository: ArticleRepository,
        *,
        canonical_url: type[CanonicalUrl] = CanonicalUrl,
    ) -> None:
        self._rss_fetcher = rss_fetcher
        self._article_repository = article_repository
        self._canonical_url = canonical_url

    async def execute(
        self,
        source: Source,
    ) -> IngestionResult:
        """Import articles from a single RSS source."""

        entries = await self._rss_fetcher.fetch(source.feed_url)

        imported = 0
        skipped = 0
        failed = 0

        seen_urls: set[str] = set()

        for entry in entries:
            try:
                result = await self._ingest_one(source.id, entry, seen_urls)
            except Exception:
                failed += 1
                continue

            if result:
                imported += 1
            else:
                skipped += 1

        return IngestionResult(
            fetched=len(entries),
            imported=imported,
            skipped=skipped,
            failed=failed,
        )

    async def _ingest_one(
        self,
        source_id: UUID,
        entry: RssEntry,
        seen_urls: set[str],
    ) -> bool:
        """
        Normalize, canonicalize, dedup, and persist a single entry.

        Returns True if the article was imported, False if skipped as a
        duplicate. Raises on persistence failure so the caller can isolate the
        failure to this entry.
        """

        canonical = self._canonical_url.parse(entry.url).value

        if not canonical:
            return False

        if canonical in seen_urls:
            return False

        seen_urls.add(canonical)

        existing = await self._article_repository.get_by_url(canonical)
        if existing is not None:
            return False

        article = Article.create(
            title=entry.title,
            url=canonical,
            summary=entry.summary,
            content=entry.content,
            source_id=source_id,
            published_at=entry.published_at,
            category_id=None,
        )

        await self._article_repository.create(article)

        return True
