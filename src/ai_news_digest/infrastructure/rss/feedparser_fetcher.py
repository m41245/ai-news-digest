from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import feedparser

from ai_news_digest.domain.models.rss_entry import RssEntry
from ai_news_digest.domain.ports.rss_fetcher import RSSFetcher


class FeedparserFetcher(RSSFetcher):
    """
    RSSFetcher implementation backed by feedparser.
    """

    async def fetch(
        self,
        feed_url: str,
    ) -> list[RssEntry]:
        """
        Fetch and normalize a single RSS feed.
        """

        feed = feedparser.parse(feed_url)

        entries: list[RssEntry] = []

        for item in feed.entries:
            entries.append(
                RssEntry(
                    title=getattr(item, "title", "").strip(),
                    url=getattr(item, "link", "").strip(),
                    summary=getattr(item, "summary", "").strip(),
                    content=getattr(item, "content", None),
                    published_at=self._parse_datetime(
                        getattr(item, "published", None),
                    ),
                )
            )

        return entries

    @staticmethod
    def _parse_datetime(
        value: str | None,
    ) -> datetime:
        """
        Convert an RSS datetime string into UTC.
        """

        if not value:
            return datetime.now(UTC)

        try:
            parsed = parsedate_to_datetime(value)

            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)

            return parsed.astimezone(UTC)

        except (TypeError, ValueError):
            return datetime.now(UTC)
