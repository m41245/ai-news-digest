"""
Real-session transaction safety tests for deterministic categorization.

These tests use a real ``AsyncSession`` backed by a PostgreSQL test container
(when Docker is available) to verify that deterministic categorization
participates in a single atomic transaction: every category, topic, topic-link
and article update is committed together or rolled back together.

They intentionally avoid mocks for the persistence layer so that commit and
rollback behavior is verified against the actual SQLAlchemy session lifecycle.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy import table as sa_table

from ai_news_digest.application.services.deterministic_article_processor import (
    deterministic_categorize,
    deterministic_summarize,
)
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source

pytestmark = pytest.mark.integration


async def _count(session, table_name: str) -> int:
    result = await session.execute(select(func.count()).select_from(sa_table(table_name)))
    return int(result.scalar_one())


async def _article_status(session, article_id) -> str | None:
    result = await session.execute(
        text("SELECT status FROM articles WHERE id = :id"), {"id": str(article_id)}
    )
    row = result.scalar_one_or_none()
    return None if row is None else str(row)


def _make_source() -> Source:
    return Source(
        id=uuid4(),
        name=f"Tx Test Source {uuid4().hex[:8]}",
        feed_url=f"https://example.com/{uuid4().hex}/feed.xml",
        website_url=None,
        description=None,
        is_active=True,
        source_type=SourceType.OTHER,
        status=SourceStatus.VERIFIED,
        created_at=datetime.now(UTC),
    )


def _make_article(source: Source, status: ArticleStatus = ArticleStatus.NEW) -> Article:
    article = Article.create(
        title="Deterministic Transaction Test Article",
        url=f"https://example.com/deterministic-tx/{uuid4()}",
        summary="Initial RSS summary.",
        content="Article body content used for deterministic processing.",
        source_id=source.id,
        published_at=datetime.now(UTC),
    )
    article.status = status
    return article


async def test_deterministic_categorize_commits_atomically(db_session, container) -> None:
    """Successful deterministic categorization persists every entity together."""
    source = await container.source_repository.create(_make_source())
    article = await container.article_repository.create(_make_article(source))

    async with container.article_repository.session.begin_nested():
        summarized = await deterministic_summarize(article)
        categorized = await deterministic_categorize(
            summarized,
            container.category_repository,
            container.topic_repository,
            container.article_repository,
        )
        await container.article_repository.update_flush_only(categorized)

    await db_session.flush()

    assert await _article_status(db_session, article.id) == ArticleStatus.CATEGORIZED.value
    assert await _count(db_session, "categories") == 1
    assert await _count(db_session, "topics") == 1
    assert await _count(db_session, "article_topics") == 1


async def test_deterministic_categorize_rolls_back_on_failure(db_session, container) -> None:
    """A failure after category/topic/link creation rolls back the whole unit."""
    source = await container.source_repository.create(_make_source())
    article = await container.article_repository.create(_make_article(source))

    class _FailingArticleRepository:
        def __init__(self, inner) -> None:
            self._inner = inner
            self.session = inner.session

        async def replace_topics_flush_only(self, article_id, topic_ids):
            raise RuntimeError("simulated link replacement failure")

        def __getattr__(self, item):
            return getattr(self._inner, item)

    failing_repo = _FailingArticleRepository(container.article_repository)

    with pytest.raises(RuntimeError, match="simulated link replacement failure"):
        async with container.article_repository.session.begin_nested():
            summarized = await deterministic_summarize(article)
            await deterministic_categorize(
                summarized,
                container.category_repository,
                container.topic_repository,
                failing_repo,
            )

    await db_session.flush()

    assert await _article_status(db_session, article.id) == ArticleStatus.NEW.value
    assert await _count(db_session, "categories") == 0
    assert await _count(db_session, "topics") == 0
    assert await _count(db_session, "article_topics") == 0


async def test_deterministic_categorize_rolls_back_on_update_failure(db_session, container) -> None:
    """A failure during the final article update rolls back prior flushes."""
    source = await container.source_repository.create(_make_source())
    article = await container.article_repository.create(_make_article(source))

    class _FailingUpdateRepository:
        def __init__(self, inner) -> None:
            self._inner = inner
            self.session = inner.session

        async def update_flush_only(self, article):
            raise RuntimeError("simulated article update failure")

        def __getattr__(self, item):
            return getattr(self._inner, item)

    failing_repo = _FailingUpdateRepository(container.article_repository)

    with pytest.raises(RuntimeError, match="simulated article update failure"):
        async with container.article_repository.session.begin_nested():
            summarized = await deterministic_summarize(article)
            categorized = await deterministic_categorize(
                summarized,
                container.category_repository,
                container.topic_repository,
                container.article_repository,
            )
            await failing_repo.update_flush_only(categorized)

    await db_session.flush()

    assert await _article_status(db_session, article.id) == ArticleStatus.NEW.value
    assert await _count(db_session, "categories") == 0
    assert await _count(db_session, "topics") == 0
    assert await _count(db_session, "article_topics") == 0


async def test_existing_repository_callers_retain_behavior(db_session, container) -> None:
    """The commit-based repository methods still persist independently."""
    source = await container.source_repository.create(_make_source())
    article = await container.article_repository.create(_make_article(source))

    assert await _article_status(db_session, article.id) == ArticleStatus.NEW.value

    article.status = ArticleStatus.SUMMARIZED
    await container.article_repository.update(article)

    await db_session.flush()
    assert await _article_status(db_session, article.id) == ArticleStatus.SUMMARIZED.value
