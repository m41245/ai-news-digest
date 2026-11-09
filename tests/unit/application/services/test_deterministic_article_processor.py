"""Unit tests for deterministic_article_processor."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.services.deterministic_article_processor import (
    deterministic_categorize,
    deterministic_category,
    deterministic_summarize,
    deterministic_topics,
    normalize_text,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.models.article import Article


def make_article(status: ArticleStatus = ArticleStatus.NEW) -> Article:
    article = Article.create(
        title="Test Article",
        url=f"https://example.com/{uuid4()}",
        summary="",
        content="Article body content.",
        source_id=uuid4(),
        published_at=datetime.now(UTC),
    )
    article.status = status
    return article


def test_normalize_text_collapses_whitespace() -> None:
    assert normalize_text("  a   b \n c ") == "a b c"


def test_deterministic_category_word_boundary() -> None:
    assert deterministic_category("data modeling techniques") != deterministic_category(
        "new language model released"
    )


async def test_deterministic_summarize_bounds_length() -> None:
    article = make_article()
    article.content = "word " * 10000
    result = await deterministic_summarize(article)
    assert len(result.summary) <= 8000
    assert result.status == ArticleStatus.SUMMARIZED


async def test_deterministic_summarize_uses_existing_summary() -> None:
    article = make_article()
    article.summary = "Existing summary text."
    result = await deterministic_summarize(article)
    assert result.summary == "Existing summary text."
    assert result.status == ArticleStatus.SUMMARIZED


async def test_deterministic_categorize_no_repositories() -> None:
    article = make_article()
    result = await deterministic_categorize(article, None, None, None)
    assert result.status == ArticleStatus.CATEGORIZED
    assert result.category_id is None


async def test_deterministic_categorize_category_failure_propagates() -> None:
    repo = AsyncMock()
    repo.get_by_name.return_value = None
    repo.create_flush_only.side_effect = RuntimeError("db fail")
    article = make_article()
    with pytest.raises(RuntimeError, match="db fail"):
        await deterministic_categorize(article, repo, None, None)


async def test_deterministic_categorize_topic_create_failure_propagates() -> None:
    category_repo = AsyncMock()
    category = MagicMock()
    category.id = uuid4()
    category_repo.get_by_name.return_value = category

    topic_repo = AsyncMock()
    topic_repo.get_by_slug.return_value = None
    topic_repo.create_flush_only.side_effect = RuntimeError("topic db fail")

    article_repo = AsyncMock()
    article = make_article()
    with pytest.raises(RuntimeError, match="topic db fail"):
        await deterministic_categorize(article, category_repo, topic_repo, article_repo)


async def test_deterministic_categorize_replace_topics_failure_propagates() -> None:
    category_repo = AsyncMock()
    category = MagicMock()
    category.id = uuid4()
    category_repo.get_by_name.return_value = category

    topic_repo = AsyncMock()
    existing_topic = MagicMock()
    existing_topic.id = uuid4()
    existing_topic.name = "OpenAI"
    topic_repo.get_by_slug.return_value = existing_topic

    article_repo = AsyncMock()
    article_repo.replace_topics_flush_only.side_effect = RuntimeError("replace fail")

    article = make_article()
    article.topics = ("OpenAI",)
    with pytest.raises(RuntimeError, match="replace fail"):
        await deterministic_categorize(article, category_repo, topic_repo, article_repo)


def test_deterministic_topics_fallback() -> None:
    from ai_news_digest.application.ai.category_vocabulary import ArticleCategory

    topics = deterministic_topics("nothing relevant here", ArticleCategory.AI_RESEARCH)
    assert len(topics) >= 1
