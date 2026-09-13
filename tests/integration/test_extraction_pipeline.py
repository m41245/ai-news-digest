"""
Integration tests for the article extraction pipeline.

These tests verify the complete extraction flow against a real PostgreSQL
database:

1. RSS article is persisted with summary/content.
2. ``ExtractArticleUseCase`` is invoked.
3. HTML is fetched, extracted, cleaned, quality-validated.
4. Article is updated with extracted content (success path) or keeps
   RSS content (fallback path).

The HTTP boundary is mocked via ``unittest.mock.patch`` so no real network
is required, but SSRF validation still runs against the target URL.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from ai_news_digest.application.use_cases.article.extract_article import (
    ContentQualityValidator,
    ExtractArticleUseCase,
)
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.infrastructure.extraction import (
    ContentCleaner,
    FetchResult,
    SsrfHttpArticleFetcher,
    StdlibHtmlExtractor,
)
from ai_news_digest.infrastructure.rss.url_safety import (
    validate_rss_http_url,
)

_HTML_ARTICLE = b"""
<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
<nav>Skip to main content</nav>
<header>Site Header</header>
<main>
<article>
<h1>Real Article Title</h1>
<p>This is the first meaningful paragraph with enough content to pass validation criteria.</p>
<p>This is the second meaningful paragraph continuing the article with sufficient length.</p>
<p>This is the third paragraph providing additional context about the subject matter.</p>
<p>This is the fourth paragraph concluding the article with final thoughts and analysis.</p>
<p>This is the fifth paragraph ensuring enough content for robust quality assessment.</p>
</article>
</main>
<footer>Site Footer</footer>
<script>console.log('ads');</script>
<style>.ad { display:none; }</style>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_extraction_pipeline_success(
    db_session,
    container,
) -> None:
    """Full pipeline: RSS article -> fetch -> extraction -> cleaning -> quality -> persistence."""
    source = Source.create(
        name="Integration Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test source for extraction integration",
    )
    source = await container.source_repository.create(source)

    article = Article.create(
        title="RSS Title Only",
        url="https://example.com/article-1",
        summary="RSS summary text",
        content=None,
        source_id=source.id,
        published_at=datetime.now(UTC),
    )
    article = await container.article_repository.create(article)

    fetcher = SsrfHttpArticleFetcher(timeout=10.0, max_response_bytes=5_000_000)
    extractor = StdlibHtmlExtractor()
    cleaner = ContentCleaner()
    validator = ContentQualityValidator(
        min_char_count=50, min_avg_paragraph_length=20
    )

    from ai_news_digest.domain.enums.extraction_method import (
        ExtractionMethod,
    )
    from ai_news_digest.domain.enums.extraction_quality import (
        ExtractionQuality,
    )

    async def mock_fetch(url: str) -> FetchResult:
        await validate_rss_http_url(url)
        return FetchResult(
            content=_HTML_ARTICLE.decode("utf-8", errors="replace"),
            method=ExtractionMethod.HTML,
            quality=ExtractionQuality.HIGH,
            extracted_at=datetime.now(UTC),
        )

    use_case = ExtractArticleUseCase(
        article_fetcher=fetcher,
        html_extractor=extractor,
        content_cleaner=cleaner,
        article_repository=container.article_repository,
        quality_validator=validator,
    )

    with patch.object(fetcher, "fetch", mock_fetch):
        result = await use_case.execute(article)

    assert result.content is not None
    assert len(result.content) > 100
    assert "meaningful paragraph" in result.content.lower()
    assert result.extraction_method.value == "html"
    assert result.extraction_quality.value in ("high", "medium")
    assert result.extracted_at is not None
    assert result.content_char_count == len(result.content)

    persisted = await container.article_repository.get_by_id(article.id)
    assert persisted is not None
    assert persisted.content == result.content
    assert persisted.extraction_method.value == "html"


@pytest.mark.asyncio
async def test_extraction_pipeline_fallback_on_fetch_failure(
    db_session,
    container,
) -> None:
    """When article fetch fails, RSS content is preserved."""
    source = Source.create(
        name="Integration Test Source 2",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test source for extraction fallback",
    )
    source = await container.source_repository.create(source)

    article = Article.create(
        title="RSS Title Only",
        url="https://example.com/article-2",
        summary="RSS summary text",
        content="Original RSS content that must be preserved",
        source_id=source.id,
        published_at=datetime.now(UTC),
    )
    article = await container.article_repository.create(article)

    fetcher = SsrfHttpArticleFetcher(timeout=5.0)
    extractor = StdlibHtmlExtractor()
    cleaner = ContentCleaner()
    validator = ContentQualityValidator(min_char_count=200)

    use_case = ExtractArticleUseCase(
        article_fetcher=fetcher,
        html_extractor=extractor,
        content_cleaner=cleaner,
        article_repository=container.article_repository,
        quality_validator=validator,
    )

    fetcher.fetch = AsyncMock(side_effect=RuntimeError("Network down"))

    result = await use_case.execute(article)

    assert result.content == "Original RSS content that must be preserved"
    assert result.extraction_quality.value == "none"
    persisted = await container.article_repository.get_by_id(article.id)
    assert persisted.content == "Original RSS content that must be preserved"


@pytest.mark.asyncio
async def test_extraction_pipeline_fallback_on_low_quality(
    db_session,
    container,
) -> None:
    """Low-quality extraction preserves RSS content."""
    source = Source.create(
        name="Integration Test Source 3",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test source for low-quality fallback",
    )
    source = await container.source_repository.create(source)

    article = Article.create(
        title="RSS Title Only",
        url="https://example.com/article-3",
        summary="RSS summary text",
        content="Original RSS content that must be preserved on low quality",
        source_id=source.id,
        published_at=datetime.now(UTC),
    )
    article = await container.article_repository.create(article)

    fetcher = SsrfHttpArticleFetcher(timeout=5.0)
    extractor = StdlibHtmlExtractor()
    cleaner = ContentCleaner()
    validator = ContentQualityValidator(min_char_count=200)

    async def mock_fetch_short(url: str) -> FetchResult:
        await validate_rss_http_url(url)
        return FetchResult(
            content="<html><p>Too short.</p></html>",
            extracted_at=datetime.now(UTC),
        )

    use_case = ExtractArticleUseCase(
        article_fetcher=fetcher,
        html_extractor=extractor,
        content_cleaner=cleaner,
        article_repository=container.article_repository,
        quality_validator=validator,
    )

    with patch.object(fetcher, "fetch", mock_fetch_short):
        result = await use_case.execute(article)

    assert result.content == "Original RSS content that must be preserved on low quality"
    assert result.extraction_quality.value == "none"
    persisted = await container.article_repository.get_by_id(article.id)
    assert persisted.content == "Original RSS content that must be preserved on low quality"


@pytest.mark.asyncio
async def test_extraction_pipeline_ssrf_rejection(
    db_session,
    container,
) -> None:
    """SSRF rejection during fetch leaves article unchanged."""
    source = Source.create(
        name="Integration Test Source 4",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test source for SSRF rejection",
    )
    source = await container.source_repository.create(source)

    article = Article.create(
        title="RSS Title Only",
        url="http://localhost/article",
        summary="RSS summary text",
        content="Original RSS content",
        source_id=source.id,
        published_at=datetime.now(UTC),
    )
    article = await container.article_repository.create(article)

    fetcher = SsrfHttpArticleFetcher(timeout=5.0)
    extractor = StdlibHtmlExtractor()
    cleaner = ContentCleaner()
    validator = ContentQualityValidator(min_char_count=10)

    use_case = ExtractArticleUseCase(
        article_fetcher=fetcher,
        html_extractor=extractor,
        content_cleaner=cleaner,
        article_repository=container.article_repository,
        quality_validator=validator,
    )

    result = await use_case.execute(article)

    assert result.content == "Original RSS content"
    assert result.extraction_quality.value == "none"


@pytest.mark.asyncio
async def test_ingestion_integration_with_extraction(
    db_session,
    container,
) -> None:
    """IngestFromSourceUseCase calls extraction after creating articles."""
    from ai_news_digest.application.use_cases.article.ingest_from_source import (
        IngestFromSourceUseCase,
    )
    from ai_news_digest.domain.models.rss_entry import RssEntry

    source = Source.create(
        name="Integration Test Source 5",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test source for ingestion+extraction",
    )
    source = await container.source_repository.create(source)

    entry = RssEntry(
        title="Ingested Article",
        url="https://example.com/ingested-article",
        summary="RSS summary",
        content="RSS content",
        published_at=datetime.now(UTC),
    )

    mock_rss_fetcher = AsyncMock()
    mock_rss_fetcher.fetch.return_value = [entry]

    async def fake_extract(article: Article) -> Article:
        article.content = "Extracted full content"
        article.extraction_method = __import__(
            "ai_news_digest.domain.enums.extraction_method",
            fromlist=["ExtractionMethod"],
        ).ExtractionMethod.HTML
        article.extraction_quality = __import__(
            "ai_news_digest.domain.enums.extraction_quality",
            fromlist=["ExtractionQuality"],
        ).ExtractionQuality.HIGH
        article.extracted_at = datetime.now(UTC)
        article.content_char_count = len("Extracted full content")
        # Persist the update
        await container.article_repository.update(article)
        return article

    mock_extract = AsyncMock()
    mock_extract.execute = AsyncMock(wraps=fake_extract)

    ingest_uc = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=container.article_repository,
        extract_article=mock_extract,
        extraction_timeout=10.0,
    )

    result = await ingest_uc.execute(source)

    assert result.imported == 1
    assert result.failed == 0
    assert mock_extract.execute.call_count == 1

    articles = await container.article_repository.list_recent(limit=10)
    source_articles = [a for a in articles if a.source_id == source.id]
    assert len(source_articles) == 1
    assert source_articles[0].content == "Extracted full content"


@pytest.mark.asyncio
async def test_ingestion_extraction_timeout_does_not_break_ingestion(
    db_session,
    container,
) -> None:
    """A timeout during extraction must not prevent article creation."""
    from ai_news_digest.application.use_cases.article.ingest_from_source import (
        IngestFromSourceUseCase,
    )
    from ai_news_digest.domain.models.rss_entry import RssEntry

    source = Source.create(
        name="Integration Test Source 6",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test source for extraction timeout",
    )
    source = await container.source_repository.create(source)

    entry = RssEntry(
        title="Timeout Article",
        url="https://example.com/timeout-article",
        summary="RSS summary",
        content="RSS content",
        published_at=datetime.now(UTC),
    )

    mock_rss_fetcher = AsyncMock()
    mock_rss_fetcher.fetch.return_value = [entry]

    async def slow_extract(article: Article) -> Article:
        await asyncio.sleep(10)
        return article

    mock_extract = AsyncMock(side_effect=slow_extract)

    ingest_uc = IngestFromSourceUseCase(
        rss_fetcher=mock_rss_fetcher,
        article_repository=container.article_repository,
        extract_article=mock_extract,
        extraction_timeout=0.1,
    )

    result = await ingest_uc.execute(source)

    assert result.imported == 1
    assert result.failed == 0

    articles = await container.article_repository.list_recent(limit=10)
    source_articles = [a for a in articles if a.source_id == source.id]
    assert len(source_articles) == 1
    assert source_articles[0].content == "RSS content"
