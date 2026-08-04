from __future__ import annotations

from dataclasses import dataclass

from ai_news_digest.application.services.rss.parser.models import (
    ParsedArticle,
)


@dataclass(slots=True, frozen=True)
class FeedResult:
    """
    Result returned after successfully processing a feed.
    """

    feed_url: str
    articles: list[ParsedArticle]
