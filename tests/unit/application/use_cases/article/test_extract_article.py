"""
Unit tests for ExtractArticleUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.use_cases.article.extract_article import (
    ContentQualityValidator,
    ExtractArticleUseCase,
)
from ai_news_digest.domain.enums.extraction_method import ExtractionMethod
from ai_news_digest.domain.enums.extraction_quality import ExtractionQuality
from ai_news_digest.domain.models.article import Article
from ai_news_digest.infrastructure.extraction.ssrf_http_client import FetchResult


@pytest.fixture
def sample_article() -> Article:
    """Create a sample article for testing."""
    return Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Original summary",
        content=None,
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_article_with_rss() -> Article:
    """Create a sample article with existing RSS content."""
    return Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Original summary",
        content="RSS content here that should be preserved on fallback.",
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )


def _make_fetch_result(
    content: str = "<html>text</html>",
    extracted_at: datetime | None = None,
) -> FetchResult:
    return FetchResult(
        content=content,
        method=ExtractionMethod.HTML,
        quality=ExtractionQuality.HIGH,
        extracted_at=extracted_at if extracted_at is not None else datetime.now(UTC),
    )


async def test_extract_article_success(
    sample_article: Article,
) -> None:
    """Test successful article extraction without quality validation."""
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(
        return_value=_make_fetch_result("<html>Extracted text</html>"),
    )

    html_extractor = MagicMock()
    html_extractor.extract = AsyncMock(return_value="Extracted text")

    content_cleaner = MagicMock()
    content_cleaner.clean = MagicMock(return_value="Cleaned text")

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article)

    use_case = ExtractArticleUseCase(
        article_fetcher=article_fetcher,
        html_extractor=html_extractor,
        content_cleaner=content_cleaner,
        article_repository=article_repository,
        quality_validator=None,
    )

    result = await use_case.execute(sample_article)

    assert result.content == "Cleaned text"
    assert result.content_char_count == len("Cleaned text")
    article_repository.update.assert_called_once_with(sample_article)


async def test_extract_article_fetch_failure(
    sample_article: Article,
) -> None:
    """Test extraction when fetch fails."""
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(side_effect=RuntimeError("Network error"))

    html_extractor = MagicMock()
    html_extractor.extract = AsyncMock()

    content_cleaner = MagicMock()
    content_cleaner.clean = MagicMock()

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article)

    use_case = ExtractArticleUseCase(
        article_fetcher=article_fetcher,
        html_extractor=html_extractor,
        content_cleaner=content_cleaner,
        article_repository=article_repository,
    )

    result = await use_case.execute(sample_article)

    assert result.content is None
    article_repository.update.assert_not_called()


async def test_extract_article_empty_content(
    sample_article: Article,
) -> None:
    """Test extraction when fetch returns empty content."""
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(return_value=_make_fetch_result(content=""))

    html_extractor = MagicMock()
    html_extractor.extract = AsyncMock()

    content_cleaner = MagicMock()
    content_cleaner.clean = MagicMock()

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article)

    use_case = ExtractArticleUseCase(
        article_fetcher=article_fetcher,
        html_extractor=html_extractor,
        content_cleaner=content_cleaner,
        article_repository=article_repository,
    )

    result = await use_case.execute(sample_article)

    assert result.content is None
    article_repository.update.assert_not_called()


async def test_extract_article_extractor_failure(
    sample_article: Article,
) -> None:
    """Test extraction when HTML extraction fails."""
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(return_value=_make_fetch_result())

    html_extractor = MagicMock()
    html_extractor.extract = AsyncMock(side_effect=RuntimeError("Extraction error"))

    content_cleaner = MagicMock()
    content_cleaner.clean = MagicMock()

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article)

    use_case = ExtractArticleUseCase(
        article_fetcher=article_fetcher,
        html_extractor=html_extractor,
        content_cleaner=content_cleaner,
        article_repository=article_repository,
    )

    result = await use_case.execute(sample_article)

    assert result.content is None
    article_repository.update.assert_not_called()


async def test_extract_article_cleaner_failure(
    sample_article: Article,
) -> None:
    """Test extraction when content cleaning fails."""
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(return_value=_make_fetch_result())

    html_extractor = MagicMock()
    html_extractor.extract = AsyncMock(return_value="Raw text")

    content_cleaner = MagicMock()
    content_cleaner.clean = MagicMock(side_effect=RuntimeError("Clean error"))

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article)

    use_case = ExtractArticleUseCase(
        article_fetcher=article_fetcher,
        html_extractor=html_extractor,
        content_cleaner=content_cleaner,
        article_repository=article_repository,
        quality_validator=None,
    )

    result = await use_case.execute(sample_article)

    assert result.content == "Raw text"
    article_repository.update.assert_called_once_with(sample_article)


async def test_extract_article_empty_extracted_text(
    sample_article: Article,
) -> None:
    """Test extraction when extractor returns empty text."""
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(return_value=_make_fetch_result())

    html_extractor = MagicMock()
    html_extractor.extract = AsyncMock(return_value="")

    content_cleaner = MagicMock()
    content_cleaner.clean = MagicMock()

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article)

    use_case = ExtractArticleUseCase(
        article_fetcher=article_fetcher,
        html_extractor=html_extractor,
        content_cleaner=content_cleaner,
        article_repository=article_repository,
    )

    result = await use_case.execute(sample_article)

    assert result.content is None
    article_repository.update.assert_not_called()


async def test_extract_article_quality_low_preserves_rss(
    sample_article_with_rss: Article,
) -> None:
    """Low quality extracted content should preserve existing RSS content."""
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(return_value=_make_fetch_result())

    html_extractor = MagicMock()
    html_extractor.extract = AsyncMock(return_value="Short.")

    content_cleaner = MagicMock()
    content_cleaner.clean = MagicMock(return_value="Short.")

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article_with_rss)

    use_case = ExtractArticleUseCase(
        article_fetcher=article_fetcher,
        html_extractor=html_extractor,
        content_cleaner=content_cleaner,
        article_repository=article_repository,
        quality_validator=ContentQualityValidator(min_char_count=200),
    )

    result = await use_case.execute(sample_article_with_rss)

    assert result.content == "RSS content here that should be preserved on fallback."
    assert result.extraction_method == ExtractionMethod.HTML
    assert result.extraction_quality.value == "none"
    assert result.extracted_at is not None
    assert result.content_char_count == len("Short.")
    article_repository.update.assert_called_once_with(sample_article_with_rss)


async def test_extract_article_quality_low_no_rss_uses_extracted(
    sample_article: Article,
) -> None:
    """Low quality with no RSS content should use extracted content."""
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(return_value=_make_fetch_result())

    html_extractor = MagicMock()
    html_extractor.extract = AsyncMock(return_value="Short.")

    content_cleaner = MagicMock()
    content_cleaner.clean = MagicMock(return_value="Short.")

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article)

    use_case = ExtractArticleUseCase(
        article_fetcher=article_fetcher,
        html_extractor=html_extractor,
        content_cleaner=content_cleaner,
        article_repository=article_repository,
        quality_validator=ContentQualityValidator(min_char_count=200),
    )

    result = await use_case.execute(sample_article)

    assert result.content == "Short."
    assert result.extraction_method == ExtractionMethod.HTML
    assert result.extraction_quality.value == "none"
    article_repository.update.assert_called_once_with(sample_article)


async def test_extract_article_quality_high_replaces_rss(
    sample_article_with_rss: Article,
) -> None:
    """High quality extracted content should replace RSS content."""
    long_content = "\n\n".join(
        "This is a meaningful paragraph with sufficient length for quality assessment."
        for _ in range(5)
    )

    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(return_value=_make_fetch_result())

    html_extractor = MagicMock()
    html_extractor.extract = AsyncMock(return_value=long_content)

    content_cleaner = MagicMock()
    content_cleaner.clean = MagicMock(return_value=long_content)

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article_with_rss)

    use_case = ExtractArticleUseCase(
        article_fetcher=article_fetcher,
        html_extractor=html_extractor,
        content_cleaner=content_cleaner,
        article_repository=article_repository,
        quality_validator=ContentQualityValidator(min_char_count=200),
    )

    result = await use_case.execute(sample_article_with_rss)

    assert result.content == long_content
    assert result.extraction_method == ExtractionMethod.HTML
    assert result.extraction_quality.value == "high"
    assert result.content_char_count == len(long_content)
    article_repository.update.assert_called_once_with(sample_article_with_rss)


async def test_extract_article_sets_metadata_on_fallback(
    sample_article_with_rss: Article,
) -> None:
    """Metadata is set correctly when content falls back to RSS."""
    extracted_at = datetime.now(UTC)
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(
        return_value=_make_fetch_result(extracted_at=extracted_at)
    )

    html_extractor = MagicMock()
    html_extractor.extract = AsyncMock(return_value="Too short.")

    content_cleaner = MagicMock()
    content_cleaner.clean = MagicMock(return_value="Too short.")

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article_with_rss)

    use_case = ExtractArticleUseCase(
        article_fetcher=article_fetcher,
        html_extractor=html_extractor,
        content_cleaner=content_cleaner,
        article_repository=article_repository,
        quality_validator=ContentQualityValidator(min_char_count=200),
    )

    result = await use_case.execute(sample_article_with_rss)

    assert result.content == "RSS content here that should be preserved on fallback."
    assert result.extraction_method == ExtractionMethod.HTML
    assert result.extraction_quality.value == "none"
    assert result.extracted_at == extracted_at
    assert result.content_char_count == len("Too short.")
    article_repository.update.assert_called_once()


async def test_extract_article_handles_fetch_ssrf_failure(
    sample_article: Article,
) -> None:
    """Test extraction when fetcher returns an SSRF failure result."""
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(
        return_value=FetchResult(
            content="",
            failure_reason=(
                "SSRF validation failed: Feed URL host 'localhost' is not permitted."
            ),
        )
    )

    html_extractor = MagicMock()
    html_extractor.extract = AsyncMock()

    content_cleaner = MagicMock()
    content_cleaner.clean = MagicMock()

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article)

    use_case = ExtractArticleUseCase(
        article_fetcher=article_fetcher,
        html_extractor=html_extractor,
        content_cleaner=content_cleaner,
        article_repository=article_repository,
    )

    result = await use_case.execute(sample_article)

    assert result.content is None
    article_repository.update.assert_not_called()


async def test_extract_article_handles_oversized_response(
    sample_article: Article,
) -> None:
    """Test extraction when fetcher returns failure due to size limit."""
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(
        return_value=FetchResult(
            content="",
            failure_reason=(
                "Article 'https://example.com/article' body exceeds the maximum "
                "allowed size (5000000 bytes)."
            ),
        )
    )

    html_extractor = MagicMock()
    html_extractor.extract = AsyncMock()

    content_cleaner = MagicMock()
    content_cleaner.clean = MagicMock()

    article_repository = MagicMock()
    article_repository.update = AsyncMock(return_value=sample_article)

    use_case = ExtractArticleUseCase(
        article_fetcher=article_fetcher,
        html_extractor=html_extractor,
        content_cleaner=content_cleaner,
        article_repository=article_repository,
    )

    result = await use_case.execute(sample_article)

    assert result.content is None
    article_repository.update.assert_not_called()
