"""
Unit tests for ListArticlesUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from ai_news_digest.application.use_cases.article.list import ListArticlesUseCase
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article


async def test_list_articles_success(mock_article_repository: AsyncMock) -> None:
    """Test successful listing of articles."""
    articles = [
        Article(
            id="12345678-1234-1234-1234-123456789abc",
            title="Article A",
            url="https://example.com/a",
            summary="Summary A",
            content="Content A",
            source_id="12345678-1234-1234-1234-123456789abc",
            category_id=None,
            published_at=datetime.now(UTC),
            fetched_at=datetime.now(UTC),
            status=ArticleStatus.NEW,
        ),
        Article(
            id="87654321-4321-4321-4321-cba987654321",
            title="Article B",
            url="https://example.com/b",
            summary="Summary B",
            content="Content B",
            source_id="12345678-1234-1234-1234-123456789abc",
            category_id="87654321-4321-4321-4321-cba987654321",
            published_at=datetime.now(UTC),
            fetched_at=datetime.now(UTC),
            status=ArticleStatus.SUMMARIZED,
        ),
    ]
    mock_article_repository.list_recent.return_value = articles

    use_case = ListArticlesUseCase(repository=mock_article_repository)

    responses = await use_case.execute()

    assert len(responses) == 2
    assert responses[0].title == "Article A"
    assert responses[1].title == "Article B"
    assert responses[1].status == "summarized"
    mock_article_repository.list_recent.assert_called_once_with(limit=100)


async def test_list_articles_empty(mock_article_repository: AsyncMock) -> None:
    """Test listing articles when none exist."""
    mock_article_repository.list_recent.return_value = []

    use_case = ListArticlesUseCase(repository=mock_article_repository)

    responses = await use_case.execute()

    assert len(responses) == 0
    mock_article_repository.list_recent.assert_called_once_with(limit=100)


async def test_list_articles_custom_limit(mock_article_repository: AsyncMock) -> None:
    """Test listing articles with custom limit."""
    mock_article_repository.list_recent.return_value = []

    use_case = ListArticlesUseCase(repository=mock_article_repository)

    await use_case.execute(limit=10)

    mock_article_repository.list_recent.assert_called_once_with(limit=10)
