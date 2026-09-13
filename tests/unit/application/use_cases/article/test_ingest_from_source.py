"""
Unit tests for IngestFromSourceUseCase.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from ai_news_digest.application.use_cases.article.ingest_from_source import (
    IngestFromSourceUseCase,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.extraction_method import ExtractionMethod
from ai_news_digest.domain.enums.extraction_quality import ExtractionQuality
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
    mock_rss_fetcher.fetch.return_value = sample_rss_entries
    mock_article_repository.get_by_url.return_value = None
    mock_article_repository.create.return_value = None

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
    )

    result = await use_case.execute(sample_source)

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

    result = await use_case.execute(sample_source)

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
    mock_rss_fetcher.fetch.return_value = sample_rss_entries

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

    result = await use_case.execute(sample_source)

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
    mock_rss_fetcher.fetch.return_value = []

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
    )

    result = await use_case.execute(sample_source)

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

    result = await use_case.execute(sample_source)

    assert result.imported == 1
    assert result.skipped == 1
    assert mock_article_repository.get_by_url.call_count == 1
    created_article = mock_article_repository.create.call_args.args[0]
    assert created_article.url == "https://example.com/article1"


async def test_ingest_from_source_intra_feed_dedup(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """Duplicate URLs within the same feed are skipped without a DB lookup."""
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

    result = await use_case.execute(sample_source)

    assert result.imported == 1
    assert result.skipped == 1
    assert mock_article_repository.get_by_url.call_count == 1


async def test_ingest_from_source_article_status_is_new(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """Newly persisted articles start in the NEW status."""
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

    await use_case.execute(sample_source)

    created_article = mock_article_repository.create.call_args.args[0]
    assert created_article.status == ArticleStatus.NEW


async def test_ingest_from_source_entry_failure_isolated(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """A failure on one entry must not stop processing of remaining entries."""
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
            url="",
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

    result = await use_case.execute(sample_source)

    assert result.fetched == 3
    assert result.imported == 2
    assert result.skipped == 1


async def test_ingest_calls_extraction_after_article_creation(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """Extraction use case is called after article is persisted."""
    entry = RssEntry(
        title="Article",
        url="https://example.com/article1",
        summary="Summary",
        content="RSS content",
        published_at=datetime.now(UTC),
    )
    mock_rss_fetcher.fetch.return_value = [entry]
    mock_article_repository.get_by_url.return_value = None

    created_articles: list[Article] = []

    def capture_create(article: Article) -> Article:
        created_articles.append(article)
        return article

    mock_article_repository.create.side_effect = capture_create

    mock_extract = AsyncMock()

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
        extract_article=mock_extract,
    )

    await use_case.execute(sample_source)

    assert mock_article_repository.create.call_count == 1
    mock_extract.execute.assert_called_once()
    called_article = mock_extract.execute.call_args.args[0]
    assert called_article.url == "https://example.com/article1"


async def test_ingest_extraction_timeout_does_not_break_ingestion(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """A timeout during extraction must not prevent article creation."""
    entry = RssEntry(
        title="Article",
        url="https://example.com/article1",
        summary="Summary",
        content="RSS content",
        published_at=datetime.now(UTC),
    )
    mock_rss_fetcher.fetch.return_value = [entry]
    mock_article_repository.get_by_url.return_value = None
    mock_article_repository.create.return_value = Article.create(
        title="Article",
        url="https://example.com/article1",
        summary="Summary",
        content="RSS content",
        source_id=sample_source.id,
        published_at=datetime.now(UTC),
    )

    async def slow_extract(article: Article) -> Article:
        await asyncio.sleep(10)
        return article

    mock_extract = AsyncMock(side_effect=slow_extract)

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
        extract_article=mock_extract,
        extraction_timeout=0.01,
    )

    result = await use_case.execute(sample_source)

    assert result.imported == 1
    assert result.failed == 0
    assert result.skipped == 0


async def test_ingest_extraction_failure_does_not_break_ingestion(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """An exception during extraction must not prevent article creation."""
    entry = RssEntry(
        title="Article",
        url="https://example.com/article1",
        summary="Summary",
        content="RSS content",
        published_at=datetime.now(UTC),
    )
    mock_rss_fetcher.fetch.return_value = [entry]
    mock_article_repository.get_by_url.return_value = None
    mock_article_repository.create.return_value = Article.create(
        title="Article",
        url="https://example.com/article1",
        summary="Summary",
        content="RSS content",
        source_id=sample_source.id,
        published_at=datetime.now(UTC),
    )

    mock_extract = AsyncMock(side_effect=RuntimeError("Extraction crashed"))

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
        extract_article=mock_extract,
    )

    result = await use_case.execute(sample_source)

    assert result.imported == 1
    assert result.failed == 0
    assert result.skipped == 0


async def test_ingest_extraction_failure_preserves_rss_content(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """When extraction fails the article keeps its original RSS content."""
    entry = RssEntry(
        title="Article",
        url="https://example.com/article1",
        summary="Summary",
        content="Original RSS content",
        published_at=datetime.now(UTC),
    )
    mock_rss_fetcher.fetch.return_value = [entry]
    mock_article_repository.get_by_url.return_value = None

    created_articles: list[Article] = []

    def capture_create(article: Article) -> Article:
        created_articles.append(article)
        return article

    mock_article_repository.create.side_effect = capture_create

    mock_extract = AsyncMock(side_effect=RuntimeError("Extraction crashed"))

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
        extract_article=mock_extract,
    )

    result = await use_case.execute(sample_source)

    assert result.imported == 1
    assert result.failed == 0
    created = created_articles[0]
    assert created.content == "Original RSS content"


async def test_ingest_successful_extraction_updates_article(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """A successful extraction mutates the article with extracted content."""
    entry = RssEntry(
        title="Article",
        url="https://example.com/article1",
        summary="Summary",
        content="RSS content",
        published_at=datetime.now(UTC),
    )
    mock_rss_fetcher.fetch.return_value = [entry]
    mock_article_repository.get_by_url.return_value = None
    mock_article_repository.create.side_effect = lambda article: article

    async def fake_extract(article: Article) -> Article:
        article.content = "Extracted full content"
        article.extraction_method = ExtractionMethod.HTML
        article.extraction_quality = ExtractionQuality.HIGH
        article.extracted_at = datetime.now(UTC)
        article.content_char_count = len("Extracted full content")
        return article

    extract_mock = AsyncMock()
    extract_mock.execute = AsyncMock(wraps=fake_extract)

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
        extract_article=extract_mock,
    )

    result = await use_case.execute(sample_source)

    assert result.imported == 1
    assert result.failed == 0
    assert mock_article_repository.create.call_count == 1
    assert extract_mock.execute.call_count == 1
    called_with = extract_mock.execute.call_args.args[0]
    assert called_with.content == "Extracted full content"
    assert called_with.extraction_method == ExtractionMethod.HTML
    assert called_with.extraction_quality == ExtractionQuality.HIGH
    assert called_with.content_char_count == len("Extracted full content")


async def test_ingest_handles_extraction_ssrf_failure(
    sample_source: Source,
    mock_article_repository: AsyncMock,
) -> None:
    """Ingestion preserves RSS content when extraction fails due to SSRF."""
    mock_rss_fetcher = AsyncMock()
    mock_rss_fetcher.fetch.return_value = [
        RssEntry(
            title="Article",
            url="https://example.com/article",
            summary="RSS summary",
            content=None,
            published_at=datetime.now(UTC),
        ),
    ]
    mock_article_repository.get_by_url.return_value = None

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
    )

    result = await use_case.execute(sample_source)

    assert result.imported == 1
    assert result.failed == 0
    created_article = mock_article_repository.create.call_args.args[0]
    assert created_article.content is None
    assert created_article.summary == "RSS summary"


async def test_ingest_handles_extraction_timeout(
    sample_source: Source,
    mock_rss_fetcher: AsyncMock,
    mock_article_repository: AsyncMock,
) -> None:
    """Ingestion handles repository timeout without crashing."""
    mock_rss_fetcher.fetch.return_value = [
        RssEntry(
            title="Article",
            url="https://example.com/article",
            summary="Summary",
            content="Content",
            published_at=datetime.now(UTC),
        ),
    ]
    mock_article_repository.get_by_url.return_value = None
    mock_article_repository.create.side_effect = TimeoutError()

    use_case = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=mock_article_repository,
    )

    result = await use_case.execute(sample_source)

    assert result.failed == 1
    assert result.imported == 0
