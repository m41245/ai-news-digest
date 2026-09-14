"""
Unit tests for SummarizeArticleUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.ai.models import AIResponse, AIUsage
from ai_news_digest.application.use_cases.article.summarize_article import (
    SummarizeArticleUseCase,
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


async def test_summarize_article_success(
    mock_provider_manager: MagicMock,
    mock_article_repository: AsyncMock,
    sample_article: Article,
) -> None:
    """Test successful article summarization."""
    mock_provider_manager.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content="Enhanced summary",
        usage=AIUsage(prompt_tokens=10, completion_tokens=5),
        latency_ms=100.0,
    )
    mock_article_repository.update.return_value = sample_article

    use_case = SummarizeArticleUseCase(
        provider_manager=mock_provider_manager,
        article_repository=mock_article_repository,
    )

    result = await use_case.execute(sample_article)

    assert result.summary == "Enhanced summary"
    assert result.status == ArticleStatus.SUMMARIZED
    mock_provider_manager.generate.assert_called_once()
    call_kwargs = mock_provider_manager.generate.call_args
    assert call_kwargs.kwargs.get("capability") == "summarization"
    mock_article_repository.update.assert_called_once_with(sample_article)


async def test_summarize_article_empty_response(
    mock_provider_manager: MagicMock,
    mock_article_repository: AsyncMock,
    sample_article: Article,
) -> None:
    """Test summarization when provider returns empty content."""
    mock_provider_manager.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content="",
        usage=AIUsage(prompt_tokens=10, completion_tokens=0),
        latency_ms=100.0,
    )
    mock_article_repository.update.return_value = sample_article

    use_case = SummarizeArticleUseCase(
        provider_manager=mock_provider_manager,
        article_repository=mock_article_repository,
    )

    result = await use_case.execute(sample_article)

    assert result.summary == "Original summary"
    assert result.status == ArticleStatus.SUMMARIZED


async def test_summarize_article_provider_raises(
    mock_provider_manager: MagicMock,
    mock_article_repository: AsyncMock,
    sample_article: Article,
) -> None:
    """Test summarization propagates provider errors."""
    mock_provider_manager.generate.side_effect = ExternalServiceError("provider down")

    use_case = SummarizeArticleUseCase(
        provider_manager=mock_provider_manager,
        article_repository=mock_article_repository,
    )

    with pytest.raises(ExternalServiceError, match="provider down"):
        await use_case.execute(sample_article)


async def test_summarize_article_whitespace_response(
    mock_provider_manager: MagicMock,
    mock_article_repository: AsyncMock,
    sample_article: Article,
) -> None:
    """Test summarization when provider returns only whitespace."""
    mock_provider_manager.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content="   ",
        usage=AIUsage(prompt_tokens=10, completion_tokens=1),
        latency_ms=100.0,
    )
    mock_article_repository.update.return_value = sample_article

    use_case = SummarizeArticleUseCase(
        provider_manager=mock_provider_manager,
        article_repository=mock_article_repository,
    )

    result = await use_case.execute(sample_article)

    assert result.summary == "Original summary"
