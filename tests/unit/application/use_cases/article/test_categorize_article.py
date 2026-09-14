"""
Unit tests for CategorizeArticleUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.ai.models import AIResponse, AIUsage
from ai_news_digest.application.use_cases.article.categorize_article import (
    CategorizeArticleUseCase,
)
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article


@pytest.fixture
def mock_provider_manager() -> MagicMock:
    """Mock ProviderManager for testing."""
    manager = MagicMock()
    manager.generate = AsyncMock()
    return manager


@pytest.fixture
def mock_article_repository() -> AsyncMock:
    """Mock ArticleRepository for testing."""
    return AsyncMock()


@pytest.fixture
def mock_category_repository() -> AsyncMock:
    """Mock CategoryRepository for testing."""
    return AsyncMock()


@pytest.fixture
def sample_article() -> Article:
    """Create a sample article for testing."""
    return Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Original summary",
        content="Full article content here",
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )


async def test_categorize_article_success(
    mock_provider_manager: MagicMock,
    mock_article_repository: AsyncMock,
    mock_category_repository: AsyncMock,
    sample_article: Article,
) -> None:
    """Test successful article categorization."""
    mock_provider_manager.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content="Technology",
        usage=AIUsage(prompt_tokens=10, completion_tokens=3),
        latency_ms=100.0,
    )
    mock_article_repository.update.return_value = sample_article
    mock_category_repository.get_by_name.return_value = None
    mock_category_repository.create.return_value = MagicMock(id=uuid4(), name="technology")

    use_case = CategorizeArticleUseCase(
        provider_manager=mock_provider_manager,
        article_repository=mock_article_repository,
        category_repository=mock_category_repository,
    )

    result = await use_case.execute(sample_article)

    assert result.status == ArticleStatus.CATEGORIZED
    mock_provider_manager.generate.assert_called_once()
    call_kwargs = mock_provider_manager.generate.call_args
    assert call_kwargs.kwargs.get("capability") == "categorization"
    mock_article_repository.update.assert_called_once_with(sample_article)


async def test_categorize_article_empty_response(
    mock_provider_manager: MagicMock,
    mock_article_repository: AsyncMock,
    mock_category_repository: AsyncMock,
    sample_article: Article,
) -> None:
    """Test categorization when provider returns empty content."""
    mock_provider_manager.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content="",
        usage=AIUsage(prompt_tokens=10, completion_tokens=0),
        latency_ms=100.0,
    )
    mock_article_repository.update.return_value = sample_article
    mock_category_repository.get_by_name.return_value = None
    mock_category_repository.create.return_value = MagicMock(id=uuid4(), name="general")

    use_case = CategorizeArticleUseCase(
        provider_manager=mock_provider_manager,
        article_repository=mock_article_repository,
        category_repository=mock_category_repository,
    )

    result = await use_case.execute(sample_article)

    assert result.status == ArticleStatus.CATEGORIZED


async def test_categorize_article_provider_raises(
    mock_provider_manager: MagicMock,
    mock_article_repository: AsyncMock,
    sample_article: Article,
) -> None:
    """Test categorization propagates provider errors."""
    mock_provider_manager.generate.side_effect = ExternalServiceError("provider down")

    use_case = CategorizeArticleUseCase(
        provider_manager=mock_provider_manager,
        article_repository=mock_article_repository,
        category_repository=MagicMock(),
    )

    with pytest.raises(ExternalServiceError, match="provider down"):
        await use_case.execute(sample_article)


async def test_categorize_article_whitespace_response(
    mock_provider_manager: MagicMock,
    mock_article_repository: AsyncMock,
    mock_category_repository: AsyncMock,
    sample_article: Article,
) -> None:
    """Test categorization when provider returns only whitespace."""
    mock_provider_manager.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content="   ",
        usage=AIUsage(prompt_tokens=10, completion_tokens=1),
        latency_ms=100.0,
    )
    mock_article_repository.update.return_value = sample_article
    mock_category_repository.get_by_name.return_value = None
    mock_category_repository.create.return_value = MagicMock(id=uuid4(), name="general")

    use_case = CategorizeArticleUseCase(
        provider_manager=mock_provider_manager,
        article_repository=mock_article_repository,
        category_repository=mock_category_repository,
    )

    result = await use_case.execute(sample_article)

    assert result.status == ArticleStatus.CATEGORIZED
