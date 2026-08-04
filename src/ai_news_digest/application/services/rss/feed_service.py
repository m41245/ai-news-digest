from __future__ import annotations

from ai_news_digest.application.services.rss.models import FeedResult
from ai_news_digest.application.services.rss.parser.models import ParsedArticle
from ai_news_digest.application.services.rss.parser.rss_parser import RSSParser
from ai_news_digest.application.services.rss.rss_client import RSSClient


class FeedService:
    """
    High-level service responsible for downloading and parsing RSS feeds.

    This service coordinates the RSS client and parser while hiding the
    implementation details from the rest of the application.
    """

    def __init__(
        self,
        client: RSSClient,
        parser: RSSParser,
    ) -> None:
        self._client = client
        self._parser = parser

    async def fetch(
        self,
        feed_url: str,
    ) -> FeedResult:
        """
        Download and parse a single feed.
        """

        xml = await self._client.fetch(feed_url)

        articles: list[ParsedArticle] = self._parser.parse(xml)

        return FeedResult(
            feed_url=feed_url,
            articles=articles,
        )

    async def fetch_many(
        self,
        feed_urls: list[str],
    ) -> list[FeedResult]:
        """
        Download and parse multiple feeds sequentially.
        """

        results: list[FeedResult] = []

        for feed_url in feed_urls:
            results.append(await self.fetch(feed_url))

        return results
