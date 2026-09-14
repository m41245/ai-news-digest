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
from ai_news_digest.domain.models.article import Article


@pytest.fixture
def mock_provider_manager() -> MagicMock:
    """Mock ProviderManager for testing."""
    manager = MagicMock()
    manager.generate = AsyncMock()
    return manager


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
    mock_provider_manager: MagicMock,
    sample_article: Article,
) -> None:
    """Test successful article analysis."""
    mock_provider_manager.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content=(
            '{"summary": "A summary of the article.", "importance_score": 0.9, '
            '"confidence": 0.8, '
            '"key_takeaways": ["Takeaway 1"], "why_it_matters": "Important", '
            '"companies": ["Acme"], "topics": ["AI"]}'
        ),
        usage=AIUsage(prompt_tokens=10, completion_tokens=5),
        latency_ms=100.0,
    )

    use_case = AnalyzeArticleUseCase(
        provider_manager=mock_provider_manager,
    )

    result = await use_case.execute(sample_article)

    assert result.importance_score == 0.9
    assert result.confidence == 0.8
    assert result.key_takeaways == ("Takeaway 1",)
    assert result.why_it_matters == "Important"
    assert result.companies == ("Acme",)
    assert result.topics == ("AI",)
    assert result.summary == "A summary of the article."
    assert result.ai_provider == "test-provider"
    assert result.ai_model == "test-model"
    assert result.ai_processed_at is not None
    mock_provider_manager.generate.assert_called_once()
    call_kwargs = mock_provider_manager.generate.call_args
    assert call_kwargs.kwargs.get("capability") == "analysis"


async def test_analyze_article_with_markdown_fences(
    mock_provider_manager: MagicMock,
    sample_article: Article,
) -> None:
    """Test analysis strips markdown code fences."""
    mock_provider_manager.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content=(
            "```json\n"
            '{"summary": "A summary.", "importance_score": 0.5, "confidence": 0.5, '
            '"key_takeaways": [], "why_it_matters": "Context", '
            '"companies": [], "topics": []}\n'
            "```"
        ),
        usage=AIUsage(prompt_tokens=10, completion_tokens=5),
        latency_ms=100.0,
    )

    use_case = AnalyzeArticleUseCase(
        provider_manager=mock_provider_manager,
    )

    result = await use_case.execute(sample_article)

    assert result.importance_score == 0.5
    assert result.confidence == 0.5


async def test_analyze_article_provider_raises(
    sample_article: Article,
) -> None:
    """Test analysis raises when provider fails."""
    use_case = AnalyzeArticleUseCase(
        provider_manager=MagicMock(),
    )
    use_case._provider_manager.generate.side_effect = ExternalServiceError(
        "No eligible providers available"
    )

    with pytest.raises(ExternalServiceError, match="No eligible providers available"):
        await use_case.execute(sample_article)


async def test_analyze_article_empty_response(
    mock_provider_manager: MagicMock,
    sample_article: Article,
) -> None:
    """Test analysis raises when provider returns empty response."""
    mock_provider_manager.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content="",
        usage=AIUsage(prompt_tokens=10, completion_tokens=5),
        latency_ms=100.0,
    )

    use_case = AnalyzeArticleUseCase(
        provider_manager=mock_provider_manager,
    )

    with pytest.raises(
        ExternalServiceError,
        match="AI provider returned an empty analysis response",
    ):
        await use_case.execute(sample_article)


async def test_analyze_article_invalid_json(
    mock_provider_manager: MagicMock,
    sample_article: Article,
) -> None:
    """Test analysis raises when provider returns invalid JSON."""
    mock_provider_manager.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content="Not valid JSON",
        usage=AIUsage(prompt_tokens=10, completion_tokens=5),
        latency_ms=100.0,
    )

    use_case = AnalyzeArticleUseCase(
        provider_manager=mock_provider_manager,
    )

    with pytest.raises(
        ExternalServiceError, match="Invalid JSON response from AI provider"
    ):
        await use_case.execute(sample_article)
