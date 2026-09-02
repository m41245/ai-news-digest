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
def mock_decision_engine() -> MagicMock:
    """Mock DecisionEngine for testing."""
    engine = MagicMock()
    engine.resolve.return_value = {"test-provider"}
    return engine


@pytest.fixture
def mock_provider() -> MagicMock:
    """Mock AI provider for testing."""
    provider = MagicMock()
    provider.generate = AsyncMock()
    return provider


@pytest.fixture
def mock_provider_registry(mock_provider: MagicMock) -> MagicMock:
    """Mock ProviderRegistry for testing."""
    registry = MagicMock()
    registry.get.return_value = mock_provider
    return registry


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
    mock_decision_engine: MagicMock,
    mock_provider_registry: MagicMock,
    mock_provider: MagicMock,
    sample_article: Article,
    mock_article_repository: AsyncMock,
    mock_category_repository: AsyncMock,
) -> None:
    """Test successful article categorization."""
    # Arrange
    mock_provider.generate.return_value = AIResponse(
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
        decision_engine=mock_decision_engine,
        provider_registry=mock_provider_registry,
        article_repository=mock_article_repository,
        category_repository=mock_category_repository,
    )

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.status == ArticleStatus.CATEGORIZED
    mock_decision_engine.resolve.assert_called_once_with({"categorization"})
    mock_provider_registry.get.assert_called_once_with("test-provider")
    mock_article_repository.update.assert_called_once_with(sample_article)


async def test_categorize_article_empty_response(
    mock_decision_engine: MagicMock,
    mock_provider_registry: MagicMock,
    mock_provider: MagicMock,
    sample_article: Article,
    mock_article_repository: AsyncMock,
    mock_category_repository: AsyncMock,
) -> None:
    """Test categorization when provider returns empty content."""
    # Arrange
    mock_provider.generate.return_value = AIResponse(
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
        decision_engine=mock_decision_engine,
        provider_registry=mock_provider_registry,
        article_repository=mock_article_repository,
        category_repository=mock_category_repository,
    )

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.status == ArticleStatus.CATEGORIZED
    # Note: The implementation sets category_id to None when response is empty
    # This is the current behavior being tested


async def test_categorize_article_no_provider(
    mock_decision_engine: MagicMock,
    mock_provider_registry: MagicMock,
    sample_article: Article,
    mock_article_repository: AsyncMock,
    mock_category_repository: AsyncMock,
) -> None:
    """Test categorization when no provider supports capability."""
    # Arrange
    mock_decision_engine.resolve.return_value = set()

    use_case = CategorizeArticleUseCase(
        decision_engine=mock_decision_engine,
        provider_registry=mock_provider_registry,
        article_repository=mock_article_repository,
        category_repository=mock_category_repository,
    )

    # Act & Assert
    with pytest.raises(ExternalServiceError, match="No AI provider currently supports"):
        await use_case.execute(sample_article)


async def test_categorize_article_whitespace_response(
    mock_decision_engine: MagicMock,
    mock_provider_registry: MagicMock,
    mock_provider: MagicMock,
    sample_article: Article,
    mock_article_repository: AsyncMock,
    mock_category_repository: AsyncMock,
) -> None:
    """Test categorization when provider returns only whitespace."""
    # Arrange
    mock_provider.generate.return_value = AIResponse(
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
        decision_engine=mock_decision_engine,
        provider_registry=mock_provider_registry,
        article_repository=mock_article_repository,
        category_repository=mock_category_repository,
    )

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.status == ArticleStatus.CATEGORIZED
