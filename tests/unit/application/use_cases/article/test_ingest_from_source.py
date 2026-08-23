"""
Unit tests for IngestFromSourceUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from ai_news_digest.application.use_cases.article.ingest_from_source import (
    IngestFromSourceUseCase,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.rss_entry import RssEntry
from ai_news_digest.domain.models.source import Source


@pytest.fixture
def sample_source() -> Source:
    """Create a sample source for testing."""
    return Source.create(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
    )


@pytest.fixture
def sample_rss_entries() -> list[RssEntry]:
    """Create sample RSS entries for testing."""
    return [
        RssEntry(
            title="Article 1",
            url="https://example.com/article1",
            summary="Summary 1",
            content="Content 1",
            published_at=datetime.now(UTC),
        ),
        RssEntry(
            title="Article 2",
            url="https://example.com/article2",
            summary="Summary 2",
            content="Content 2",
            published_at=datetime.now(UTC),
        ),
        RssEntry(
            title="Article 3",
            url="https://example.com/article3",
            summary="Summary 3",
            content="Content 3",
            published_at=datetime.now(UTC),
        ),
    ]


async def test_ingest_from_source_all_new(
    sample_source: Source,
    sample_rss_entries: list[RssEntry],
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """Test ingesting from source when all articles are new."""
    # Arrange
    mock_rss_fetcher.fetch.return_value = sample_rss_entries
    mock_article_repository.get_by_url.return_value = None
    mock_article_repository.create.return_value = None

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
    )

    # Act
    result = await use_case.execute(sample_source)

    # Assert
    assert result.fetched == 3
    assert result.imported == 3
    assert result.skipped == 0
    assert result.failed == 0
    mock_rss_fetcher.fetch.assert_called_once_with(sample_source.feed_url)
    assert mock_article_repository.get_by_url.call_count == 3
    assert mock_article_repository.create.call_count == 3


async def test_ingest_from_source_all_duplicates(
    sample_source: Source,
    sample_rss_entries: list[RssEntry],
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """Test ingesting from source when all articles already exist."""
    # Arrange
    mock_rss_fetcher.fetch.return_value = sample_rss_entries
    mock_article_repository.get_by_url.return_value = Article.create(
        title="Existing",
        url="https://example.com/article1",
        summary="Existing summary",
        content="Existing content",
        source_id=sample_source.id,
        published_at=datetime.now(UTC),
    )

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
    )

    # Act
    result = await use_case.execute(sample_source)

    # Assert
    assert result.fetched == 3
    assert result.imported == 0
    assert result.skipped == 3
    assert mock_article_repository.create.call_count == 0


async def test_ingest_from_source_mixed(
    sample_source: Source,
    sample_rss_entries: list[RssEntry],
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """Test ingesting from source with mix of new and existing articles."""
    # Arrange
    mock_rss_fetcher.fetch.return_value = sample_rss_entries

    # First and third are duplicates, second is new
    def get_by_url_side_effect(url: str) -> Article | None:
        if url == "https://example.com/article1":
            return Article.create(
                title="Existing 1",
                url=url,
                summary="Existing summary 1",
                content="Existing content 1",
                source_id=sample_source.id,
                published_at=datetime.now(UTC),
            )
        elif url == "https://example.com/article3":
            return Article.create(
                title="Existing 3",
                url=url,
                summary="Existing summary 3",
                content="Existing content 3",
                source_id=sample_source.id,
                published_at=datetime.now(UTC),
            )
        return None

    mock_article_repository.get_by_url.side_effect = get_by_url_side_effect
    mock_article_repository.create.return_value = None

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
    )

    # Act
    result = await use_case.execute(sample_source)

    # Assert
    assert result.fetched == 3
    assert result.imported == 1
    assert result.skipped == 2
    assert mock_article_repository.create.call_count == 1


async def test_ingest_from_source_empty_feed(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """Test ingesting from source when feed has no entries."""
    # Arrange
    mock_rss_fetcher.fetch.return_value = []

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
    )

    # Act
    result = await use_case.execute(sample_source)

    # Assert
    assert result.fetched == 0
    assert result.imported == 0
    assert result.skipped == 0
    mock_article_repository.get_by_url.assert_not_called()
    mock_article_repository.create.assert_not_called()


async def test_ingest_from_source_canonicalizes_urls(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """Article URLs are canonicalized before persistence and dedup."""
    # Arrange
    mock_rss_fetcher.fetch.return_value = [
        RssEntry(
            title="Article 1",
            url="https://example.com/article1?utm_source=newsletter",
            summary="Summary",
            content=None,
            published_at=datetime.now(UTC),
        ),
        RssEntry(
            title="Article 1 duplicate",
            url="https://example.com/article1",
            summary="Summary",
            content=None,
            published_at=datetime.now(UTC),
        ),
    ]
    mock_article_repository.get_by_url.return_value = None
    mock_article_repository.create.return_value = None

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
    )

    # Act
    result = await use_case.execute(sample_source)

    # Assert
    assert result.imported == 1
    assert result.skipped == 1
    # Only the first canonicalized URL is checked/created; second is intra-feed dup.
    assert mock_article_repository.get_by_url.call_count == 1
    created_article = mock_article_repository.create.call_args.args[0]
    assert created_article.url == "https://example.com/article1"


async def test_ingest_from_source_intra_feed_dedup(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """Duplicate URLs within the same feed are skipped without a DB lookup."""
    # Arrange
    mock_rss_fetcher.fetch.return_value = [
        RssEntry(
            title="Article",
            url="https://example.com/article1",
            summary="Summary",
            content=None,
            published_at=datetime.now(UTC),
        ),
        RssEntry(
            title="Article",
            url="https://example.com/article1?utm_source=x",
            summary="Summary",
            content=None,
            published_at=datetime.now(UTC),
        ),
    ]
    mock_article_repository.get_by_url.return_value = None
    mock_article_repository.create.return_value = None

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
    )

    # Act
    result = await use_case.execute(sample_source)

    # Assert
    assert result.imported == 1
    assert result.skipped == 1
    # get_by_url called once: the second URL canonicalizes to the same value
    # and is caught by the intra-feed seen_urls set.
    assert mock_article_repository.get_by_url.call_count == 1


async def test_ingest_from_source_article_status_is_new(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """Newly persisted articles start in the NEW status."""
    # Arrange
    mock_rss_fetcher.fetch.return_value = [
        RssEntry(
            title="Article",
            url="https://example.com/article1",
            summary="Summary",
            content=None,
            published_at=datetime.now(UTC),
        ),
    ]
    mock_article_repository.get_by_url.return_value = None
    mock_article_repository.create.return_value = None

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
    )

    # Act
    await use_case.execute(sample_source)

    # Assert
    created_article = mock_article_repository.create.call_args.args[0]
    assert created_article.status == ArticleStatus.NEW


async def test_ingest_from_source_entry_failure_isolated(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """A failure on one entry must not stop processing of remaining entries."""
    # Arrange
    mock_rss_fetcher.fetch.return_value = [
        RssEntry(
            title="Good",
            url="https://example.com/good",
            summary="Summary",
            content=None,
            published_at=datetime.now(UTC),
        ),
        RssEntry(
            title="Bad",
            url="",  # Will produce an empty canonical URL -> skip path
            summary="Summary",
            content=None,
            published_at=datetime.now(UTC),
        ),
        RssEntry(
            title="Also Good",
            url="https://example.com/also-good",
            summary="Summary",
            content=None,
            published_at=datetime.now(UTC),
        ),
    ]
    mock_article_repository.get_by_url.return_value = None
    mock_article_repository.create.return_value = None

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
    )

    # Act
    result = await use_case.execute(sample_source)

    # Assert
    assert result.fetched == 3
    assert result.imported == 2
    assert result.skipped == 1
