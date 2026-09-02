"""
Unit tests for IngestionService.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from ai_news_digest.application.services.ingestion.ingestion_service import (
    IngestionService,
)
from ai_news_digest.application.services.rss.exceptions import RSSException
from ai_news_digest.application.services.rss.models import FeedResult
from ai_news_digest.application.services.rss.parser.models import ParsedArticle
from ai_news_digest.domain.models.source import Source


@pytest.fixture
def sample_sources() -> list[Source]:
    """Create sample sources for testing."""
    return [
        Source.create(
            name="Source 1",
            feed_url="https://example1.com/feed.xml",
            is_active=True,
        ),
        Source.create(
            name="Source 2",
            feed_url="https://example2.com/feed.xml",
            is_active=True,
        ),
    ]


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
        ParsedArticle(
            title="Article 2",
            url="https://example.com/article2",
            summary="Summary 2",
            published_at=datetime.now(UTC),
        ),
    ]


async def test_ingestion_service_success(
    sample_sources: list[Source],
    sample_parsed_articles: list[ParsedArticle],
    mock_source_repository: AsyncMock,
    mock_article_repository: AsyncMock,
    mock_feed_service: AsyncMock,
) -> None:
    """Test successful ingestion cycle."""
    # Arrange
    mock_source_repository.list_active.return_value = sample_sources
    mock_feed_service.fetch.return_value = FeedResult(
        feed_url=sample_sources[0].feed_url,
        articles=sample_parsed_articles,
    )
    mock_article_repository.get_by_url.return_value = None
    mock_article_repository.create_from_parsed.return_value = None

    service = IngestionService(
        source_repository=mock_source_repository,
        article_repository=mock_article_repository,
        feed_service=mock_feed_service,
    )

    # Act
    result = await service.ingest()

    # Assert
    assert result.feeds_processed == 2
    assert result.failed_feeds == 0
    assert result.articles_fetched == 4  # 2 articles * 2 sources
    assert result.articles_inserted == 4
    assert result.articles_skipped == 0


async def test_ingestion_service_with_duplicates(
    sample_sources: list[Source],
    sample_parsed_articles: list[ParsedArticle],
    mock_source_repository: AsyncMock,
    mock_article_repository: AsyncMock,
    mock_feed_service: AsyncMock,
) -> None:
    """Test ingestion with duplicate articles."""
    # Arrange
    mock_source_repository.list_active.return_value = sample_sources
    mock_feed_service.fetch.return_value = FeedResult(
        feed_url=sample_sources[0].feed_url,
        articles=sample_parsed_articles,
    )

    # First article exists, second is new
    async def get_by_url_side_effect(url: str) -> bool | None:
        if url == "https://example.com/article1":
            return True  # Existing
        return None

    mock_article_repository.get_by_url.side_effect = get_by_url_side_effect
    mock_article_repository.create_from_parsed.return_value = None

    service = IngestionService(
        source_repository=mock_source_repository,
        article_repository=mock_article_repository,
        feed_service=mock_feed_service,
    )

    # Act
    result = await service.ingest()

    # Assert
    assert result.feeds_processed == 2
    assert result.articles_fetched == 4
    assert result.articles_inserted == 2  # Only new articles
    assert result.articles_skipped == 2  # Duplicates


async def test_ingestion_service_feed_failure(
    sample_sources: list[Source],
    mock_source_repository: AsyncMock,
    mock_article_repository: AsyncMock,
    mock_feed_service: AsyncMock,
) -> None:
    """Test ingestion when a feed fails to fetch."""
    # Arrange
    mock_source_repository.list_active.return_value = sample_sources
    mock_feed_service.fetch.side_effect = RSSException("Feed error")

    service = IngestionService(
        source_repository=mock_source_repository,
        article_repository=mock_article_repository,
        feed_service=mock_feed_service,
    )

    # Act
    result = await service.ingest()

    # Assert
    assert result.feeds_processed == 0
    assert result.failed_feeds == 2
    assert result.articles_fetched == 0
    assert result.articles_inserted == 0


async def test_ingestion_service_no_sources(
    mock_source_repository: AsyncMock,
    mock_article_repository: AsyncMock,
    mock_feed_service: AsyncMock,
) -> None:
    """Test ingestion when no active sources exist."""
    # Arrange
    mock_source_repository.list_active.return_value = []

    service = IngestionService(
        source_repository=mock_source_repository,
        article_repository=mock_article_repository,
        feed_service=mock_feed_service,
    )

    # Act
    result = await service.ingest()

    # Assert
    assert result.feeds_processed == 0
    assert result.failed_feeds == 0
    assert result.articles_fetched == 0
    assert result.articles_inserted == 0
    mock_feed_service.fetch.assert_not_called()
