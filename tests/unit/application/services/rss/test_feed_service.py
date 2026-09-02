"""
Unit tests for FeedService.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from ai_news_digest.application.services.rss.feed_service import FeedService
from ai_news_digest.application.services.rss.parser.models import ParsedArticle


@pytest.fixture
def sample_xml() -> str:
    """Sample RSS XML for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article 1</title>
      <link>https://example.com/article1</link>
      <description>Summary 1</description>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def sample_parsed_articles() -> list[ParsedArticle]:
    """Create sample parsed articles for testing."""
    return [
        ParsedArticle(
            title="Article 1",
            url="https://example.com/article1",
            summary="Summary 1",
            published_at=datetime.now(UTC),
        ),
    ]


async def test_feed_service_fetch_success(
    sample_xml: str,
    sample_parsed_articles: list[ParsedArticle],
    mock_rss_client: AsyncMock,
    mock_rss_parser: AsyncMock,
) -> None:
    """Test successful feed fetch."""
    # Arrange
    mock_rss_client.fetch.return_value = sample_xml
    mock_rss_parser.parse.return_value = sample_parsed_articles

    service = FeedService(
        client=mock_rss_client,
        parser=mock_rss_parser,
    )

    # Act
    result = await service.fetch("https://example.com/feed.xml")

    # Assert
    assert result.feed_url == "https://example.com/feed.xml"
    assert len(result.articles) == 1
    assert result.articles[0].title == "Article 1"
    mock_rss_client.fetch.assert_called_once_with("https://example.com/feed.xml")
    mock_rss_parser.parse.assert_called_once_with(sample_xml)


async def test_feed_service_fetch_many(
    sample_xml: str,
    sample_parsed_articles: list[ParsedArticle],
    mock_rss_client: AsyncMock,
    mock_rss_parser: AsyncMock,
) -> None:
    """Test fetching multiple feeds sequentially."""
    # Arrange
    mock_rss_client.fetch.return_value = sample_xml
    mock_rss_parser.parse.return_value = sample_parsed_articles

    service = FeedService(
        client=mock_rss_client,
        parser=mock_rss_parser,
    )

    # Act
    results = await service.fetch_many(
        [
            "https://example1.com/feed.xml",
            "https://example2.com/feed.xml",
        ]
    )

    # Assert
    assert len(results) == 2
    assert results[0].feed_url == "https://example1.com/feed.xml"
    assert results[1].feed_url == "https://example2.com/feed.xml"
    assert mock_rss_client.fetch.call_count == 2


async def test_feed_service_empty_feed(
    sample_xml: str,
    mock_rss_client: AsyncMock,
    mock_rss_parser: AsyncMock,
) -> None:
    """Test fetching a feed with no articles."""
    # Arrange
    mock_rss_client.fetch.return_value = sample_xml
    mock_rss_parser.parse.return_value = []

    service = FeedService(
        client=mock_rss_client,
        parser=mock_rss_parser,
    )

    # Act
    result = await service.fetch("https://example.com/feed.xml")

    # Assert
    assert result.feed_url == "https://example.com/feed.xml"
    assert len(result.articles) == 0
