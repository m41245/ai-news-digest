"""
Unit tests for ProcessArticleUseCase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from ai_news_digest.application.use_cases.article.process_article import (
    ProcessArticleUseCase,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article


@pytest.fixture
def sample_article() -> Article:
    return Article.create(
        title="Test Article",
        url="https://example.com/article",
        summary="Original summary",
        content="Full content",
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )


async def test_process_article_summarizes_then_categorizes(
    sample_article: Article,
) -> None:
    """A NEW article is summarized then categorized."""
    summarized = Article.create(
        title=sample_article.title,
        url=sample_article.url,
        summary="Enhanced summary",
        content=sample_article.content,
        source_id=sample_article.source_id,
        published_at=sample_article.published_at,
    )
    summarized.status = ArticleStatus.SUMMARIZED

    categorized = Article.create(
        title=sample_article.title,
        url=sample_article.url,
        summary="Enhanced summary",
        content=sample_article.content,
        source_id=sample_article.source_id,
        published_at=sample_article.published_at,
    )
    categorized.status = ArticleStatus.CATEGORIZED

    summarize = AsyncMock()
    summarize.execute.return_value = summarized
    categorize = AsyncMock()
    categorize.execute.return_value = categorized
    repository = AsyncMock()
    repository.update.return_value = categorized

    use_case = ProcessArticleUseCase(summarize, categorize, repository)
    result = await use_case.execute(sample_article)

    assert result.status == ArticleStatus.CATEGORIZED
    summarize.execute.assert_awaited_once_with(sample_article)
    categorize.execute.assert_awaited_once()
    repository.update.assert_awaited_once()


async def test_process_article_skips_summarize_if_already_summarized() -> None:
    """A SUMMARIZED article is only categorized."""
    article = Article.create(
        title="T",
        url="https://example.com/u",
        summary="S",
        content="C",
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )
    article.status = ArticleStatus.SUMMARIZED

    categorized = Article.create(
        title="T",
        url="https://example.com/u",
        summary="S",
        content="C",
        source_id=article.source_id,
        published_at=article.published_at,
    )
    categorized.status = ArticleStatus.CATEGORIZED

    summarize = AsyncMock()
    categorize = AsyncMock()
    categorize.execute.return_value = categorized
    repository = AsyncMock()
    repository.update.return_value = categorized

    use_case = ProcessArticleUseCase(summarize, categorize, repository)
    result = await use_case.execute(article)

    assert result.status == ArticleStatus.CATEGORIZED
    summarize.execute.assert_not_awaited()
    categorize.execute.assert_awaited_once()


async def test_process_article_idempotent_when_already_categorized() -> None:
    """A CATEGORIZED article is not reprocessed."""
    article = Article.create(
        title="T",
        url="https://example.com/u",
        summary="S",
        content="C",
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )
    article.status = ArticleStatus.CATEGORIZED

    summarize = AsyncMock()
    categorize = AsyncMock()
    repository = AsyncMock()
    repository.update.return_value = article

    use_case = ProcessArticleUseCase(summarize, categorize, repository)
    result = await use_case.execute(article)

    assert result.status == ArticleStatus.CATEGORIZED
    summarize.execute.assert_not_awaited()
    categorize.execute.assert_not_awaited()
