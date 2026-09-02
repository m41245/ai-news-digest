"""
Unit tests for CreateArticleUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from ai_news_digest.application.dto.article import CreateArticleRequest
from ai_news_digest.application.exceptions.article import ArticleAlreadyExistsError
from ai_news_digest.application.use_cases.article.create import CreateArticleUseCase
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article


async def test_create_article_success(mock_article_repository: AsyncMock) -> None:
    """Test successful article creation."""
    request = CreateArticleRequest(
        title="Test Article",
        url="https://example.com/test",
        summary="Test summary",
        content="Test content",
        source_id="12345678-1234-1234-1234-123456789abc",
        published_at="2024-01-01T00:00:00+00:00",
        category_id="87654321-4321-4321-4321-cba987654321",
    )

    mock_article_repository.get_by_url.return_value = None
    created_article = Article(
        id=request.source_id,
        title=request.title,
        url=request.url,
        summary=request.summary,
        content=request.content,
        source_id=request.source_id,
        category_id=request.category_id,
        published_at=datetime.fromisoformat(request.published_at),
        fetched_at=datetime.now(UTC),
        status=ArticleStatus.NEW,
    )
    mock_article_repository.create.return_value = created_article

    use_case = CreateArticleUseCase(repository=mock_article_repository)

    response = await use_case.execute(request)

    assert response.title == "Test Article"
    assert response.url == "https://example.com/test"
    assert response.summary == "Test summary"
    assert response.content == "Test content"
    assert response.source_id == request.source_id
    assert response.category_id == request.category_id
    assert response.status == "new"
    mock_article_repository.get_by_url.assert_called_once_with(request.url)
    mock_article_repository.create.assert_called_once()


async def test_create_article_duplicate_url(mock_article_repository: AsyncMock) -> None:
    """Test article creation fails when URL already exists."""
    request = CreateArticleRequest(
        title="Test Article",
        url="https://example.com/test",
        summary="Test summary",
        content="Test content",
        source_id="12345678-1234-1234-1234-123456789abc",
        published_at="2024-01-01T00:00:00+00:00",
    )

    existing_article = Article(
        id="12345678-1234-1234-1234-123456789abc",
        title="Existing Article",
        url=request.url,
        summary="Existing summary",
        content="Existing content",
        source_id="12345678-1234-1234-1234-123456789abc",
        category_id=None,
        published_at=datetime.fromisoformat(request.published_at),
        fetched_at=datetime.now(UTC),
        status=ArticleStatus.NEW,
    )
    mock_article_repository.get_by_url.return_value = existing_article

    use_case = CreateArticleUseCase(repository=mock_article_repository)

    with pytest.raises(ArticleAlreadyExistsError, match=request.url):
        await use_case.execute(request)

    mock_article_repository.create.assert_not_called()


async def test_create_article_minimal(mock_article_repository: AsyncMock) -> None:
    """Test article creation with minimal parameters."""
    request = CreateArticleRequest(
        title="Test Article",
        url="https://example.com/test",
        summary="Test summary",
        content=None,
        source_id="12345678-1234-1234-1234-123456789abc",
        published_at="2024-01-01T00:00:00+00:00",
    )

    mock_article_repository.get_by_url.return_value = None
    created_article = Article(
        id="12345678-1234-1234-1234-123456789abc",
        title=request.title,
        url=request.url,
        summary=request.summary,
        content=request.content,
        source_id=request.source_id,
        category_id=None,
        published_at=datetime.fromisoformat(request.published_at),
        fetched_at=datetime.now(UTC),
        status=ArticleStatus.NEW,
    )
    mock_article_repository.create.return_value = created_article

    use_case = CreateArticleUseCase(repository=mock_article_repository)

    response = await use_case.execute(request)

    assert response.title == "Test Article"
    assert response.content is None
    assert response.category_id is None
