"""
Unit tests for DeleteArticleUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ai_news_digest.application.exceptions.article import ArticleNotFoundError
from ai_news_digest.application.use_cases.article.delete import DeleteArticleUseCase
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article


async def test_delete_article_success(mock_article_repository: AsyncMock) -> None:
    """Test successful article deletion."""
    article_id = uuid4()
    existing_article = Article(
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
    mock_article_repository.get_by_id.return_value = existing_article
    mock_article_repository.delete.return_value = None

    use_case = DeleteArticleUseCase(repository=mock_article_repository)

    await use_case.execute(article_id)

    mock_article_repository.get_by_id.assert_called_once_with(article_id)
    mock_article_repository.delete.assert_called_once_with(article_id)


async def test_delete_article_not_found(mock_article_repository: AsyncMock) -> None:
    """Test article deletion fails when article does not exist."""
    article_id = uuid4()
    mock_article_repository.get_by_id.return_value = None

    use_case = DeleteArticleUseCase(repository=mock_article_repository)

    with pytest.raises(ArticleNotFoundError, match=str(article_id)):
        await use_case.execute(article_id)

    mock_article_repository.delete.assert_not_called()
