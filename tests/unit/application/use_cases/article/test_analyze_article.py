"""
Unit tests for AnalyzeArticleUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.ai.models import AIResponse, AIUsage
from ai_news_digest.application.use_cases.article.analyze_article import (
    AnalyzeArticleUseCase,
)
from ai_news_digest.core.exceptions import ExternalServiceError
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article


@pytest.fixture
def mock_provider() -> MagicMock:
    """Mock AI provider for testing."""
    provider = MagicMock()
    provider.generate = AsyncMock()
    provider.id = "test-provider"
    provider.priority = MagicMock(return_value=1)
    return provider


@pytest.fixture
def mock_provider_registry(mock_provider: MagicMock) -> MagicMock:
    """Mock ProviderRegistry for testing."""
    registry = MagicMock()
    registry.get.return_value = mock_provider
    registry.exists.return_value = True
    return registry


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


async def test_analyze_article_success(
    mock_provider_registry: MagicMock,
    mock_provider: MagicMock,
    sample_article: Article,
) -> None:
    """Test successful article analysis."""
    # Arrange
    mock_provider.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content='{"importance_score": 0.9, "confidence": 0.8, "key_takeaways": ["Takeaway 1"], "why_it_matters": "Important", "companies": ["Acme"], "topics": ["AI"]}',
        usage=AIUsage(prompt_tokens=10, completion_tokens=5),
        latency_ms=100.0,
    )

    use_case = AnalyzeArticleUseCase(
        provider_registry=mock_provider_registry,
        provider_id="test-provider",
    )

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.importance_score == 0.9
    assert result.confidence == 0.8
    assert result.key_takeaways == ("Takeaway 1",)
    assert result.why_it_matters == "Important"
    assert result.companies == ("Acme",)
    assert result.topics == ("AI",)
    mock_provider.generate.assert_called_once()


async def test_analyze_article_with_markdown_fences(
    mock_provider_registry: MagicMock,
    mock_provider: MagicMock,
    sample_article: Article,
) -> None:
    """Test analysis strips markdown code fences."""
    # Arrange
    mock_provider.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content='```json\n{"importance_score": 0.5, "confidence": 0.5, "key_takeaways": [], "why_it_matters": "", "companies": [], "topics": []}\n```',
        usage=AIUsage(prompt_tokens=10, completion_tokens=5),
        latency_ms=100.0,
    )

    use_case = AnalyzeArticleUseCase(
        provider_registry=mock_provider_registry,
        provider_id="test-provider",
    )

    # Act
    result = await use_case.execute(sample_article)

    # Assert
    assert result.importance_score == 0.5
    assert result.confidence == 0.5


async def test_analyze_article_no_provider(
    sample_article: Article,
) -> None:
    """Test analysis raises when no provider supports analysis."""
    # Arrange
    use_case = AnalyzeArticleUseCase(
        provider_registry=MagicMock(),
        provider_id=None,
    )

    # Act / Assert
    with pytest.raises(ExternalServiceError, match="No AI provider currently supports the analysis capability"):
        await use_case.execute(sample_article)


async def test_analyze_article_empty_response(
    mock_provider_registry: MagicMock,
    mock_provider: MagicMock,
    sample_article: Article,
) -> None:
    """Test analysis raises when provider returns empty response."""
    # Arrange
    mock_provider.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content="",
        usage=AIUsage(prompt_tokens=10, completion_tokens=5),
        latency_ms=100.0,
    )

    use_case = AnalyzeArticleUseCase(
        provider_registry=mock_provider_registry,
        provider_id="test-provider",
    )

    # Act / Assert
    with pytest.raises(ExternalServiceError, match="AI provider returned an empty analysis response"):
        await use_case.execute(sample_article)


async def test_analyze_article_invalid_json(
    mock_provider_registry: MagicMock,
    mock_provider: MagicMock,
    sample_article: Article,
) -> None:
    """Test analysis raises when provider returns invalid JSON."""
    # Arrange
    mock_provider.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content="Not valid JSON",
        usage=AIUsage(prompt_tokens=10, completion_tokens=5),
        latency_ms=100.0,
    )

    use_case = AnalyzeArticleUseCase(
        provider_registry=mock_provider_registry,
        provider_id="test-provider",
    )

    # Act / Assert
    with pytest.raises(ExternalServiceError, match="Invalid JSON response from AI provider"):
        await use_case.execute(sample_article)
