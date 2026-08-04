from __future__ import annotations

from abc import ABC, abstractmethod

from ai_news_digest.domain.models.rss_entry import RssEntry


class RSSFetcher(ABC):
    """
    Retrieves and normalizes RSS feeds.
    """

    @abstractmethod
    async def fetch(
        self,
        feed_url: str,
    ) -> list[RssEntry]:
        """
        Fetch and normalize a feed.
        """
        raise NotImplementedError
