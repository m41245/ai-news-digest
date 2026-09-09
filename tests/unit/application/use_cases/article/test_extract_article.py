"""
Unit tests for ExtractArticleUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.use_cases.article.extract_article import (
    ExtractArticleUseCase,
)
from ai_news_digest.domain.models.article import Article


class MockFetchResult:
    """Mock fetch result."""

    def __init__(
        self,
        content: str,
        method: str = "test",
        quality: str = "high",
        extracted_at: datetime | None = None,
    ) -> None:
        self.content = content
        self.method = method
        self.quality = quality
        self.extracted_at = extracted_at or datetime.now(UTC)


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


async def test_extract_article_success(
    sample_article: Article,
) -> None:
    """Test successful article extraction."""
    # Arrange
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(
        return_value=MockFetchResult(content="<html>Extracted text</html>"),
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
    )

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.content == "Cleaned text"
    assert result.content_char_count == len("Cleaned text")
    article_repository.update.assert_called_once_with(sample_article)


async def test_extract_article_fetch_failure(
    sample_article: Article,
) -> None:
    """Test extraction when fetch fails."""
    # Arrange
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

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.content is None
    article_repository.update.assert_not_called()


async def test_extract_article_empty_content(
    sample_article: Article,
) -> None:
    """Test extraction when fetch returns empty content."""
    # Arrange
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(return_value=MockFetchResult(content=""))

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

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.content is None
    article_repository.update.assert_not_called()


async def test_extract_article_extractor_failure(
    sample_article: Article,
) -> None:
    """Test extraction when HTML extraction fails."""
    # Arrange
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(return_value=MockFetchResult(content="<html>text</html>"))

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

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.content is None
    article_repository.update.assert_not_called()


async def test_extract_article_cleaner_failure(
    sample_article: Article,
) -> None:
    """Test extraction when content cleaning fails."""
    # Arrange
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(return_value=MockFetchResult(content="<html>text</html>"))

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
    )

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.content == "Raw text"
    article_repository.update.assert_called_once_with(sample_article)


async def test_extract_article_empty_extracted_text(
    sample_article: Article,
) -> None:
    """Test extraction when extractor returns empty text."""
    # Arrange
    article_fetcher = MagicMock()
    article_fetcher.fetch = AsyncMock(return_value=MockFetchResult(content="<html></html>"))

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

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.content is None
    article_repository.update.assert_not_called()
