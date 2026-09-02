"""
Unit tests for GetArticleUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ai_news_digest.application.exceptions.article import ArticleNotFoundError
from ai_news_digest.application.use_cases.article.get import GetArticleUseCase
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article


async def test_get_article_success(mock_article_repository: AsyncMock) -> None:
    """Test successful article retrieval."""
    article_id = uuid4()
    article = Article(
        id=article_id,
        title="Test Article",
        url="https://example.com/test",
        summary="Test summary",
        content="Test content",
        source_id=uuid4(),
        category_id=None,
        published_at=datetime.now(UTC),
        fetched_at=datetime.now(UTC),
        status=ArticleStatus.NEW,
    )
    mock_article_repository.get_by_id.return_value = article

    use_case = GetArticleUseCase(repository=mock_article_repository)

    response = await use_case.execute(article_id)

    assert response.title == "Test Article"
    assert response.url == "https://example.com/test"
    assert response.summary == "Test summary"
    assert response.content == "Test content"
    assert str(response.source_id) == str(article.source_id)
    mock_article_repository.get_by_id.assert_called_once_with(article_id)


async def test_get_article_not_found(mock_article_repository: AsyncMock) -> None:
    """Test article retrieval fails when article does not exist."""
    article_id = uuid4()
    mock_article_repository.get_by_id.return_value = None

    use_case = GetArticleUseCase(repository=mock_article_repository)

    with pytest.raises(ArticleNotFoundError, match=str(article_id)):
        await use_case.execute(article_id)

    mock_article_repository.get_by_id.assert_called_once_with(article_id)
