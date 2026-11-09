"""
Real-session transaction-safety regression tests for the deterministic worker
entry points.

These tests exercise the real ``_summarize_article_impl``,
``_categorize_article_impl``, ``_process_article_impl`` and
``_analyze_article_impl`` implementations against a real SQLAlchemy
``AsyncSession`` backed by a PostgreSQL testcontainer.

Design: each task owns a fresh session (``get_container()``). The initial
``get_by_id()`` SELECT autobegins the transaction. Deterministic flush-only
writes run inside that same transaction and are committed exactly once via an
explicit ``session.commit()`` on success and rolled back via
``session.rollback()`` on failure. The AI path is left untouched
(``repository.update()`` commits internally), so AI-enabled behavior is
preserved. ``session.begin()`` is never called after ``get_by_id()``, so
``InvalidRequestError: A transaction is already begun on this Session`` cannot
occur.

They intentionally do NOT mock ``session.begin()``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from ai_news_digest.bootstrap.container import Container
from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.source_status import SourceStatus
from ai_news_digest.domain.enums.source_type import SourceType
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.source import Source
from ai_news_digest.infrastructure.database.models.article_topic_model import (
    ArticleTopicModel,
)
from ai_news_digest.infrastructure.database.models.category_model import (
    CategoryModel,
)
from ai_news_digest.infrastructure.database.models.topic_model import TopicModel
from ai_news_digest.infrastructure.database.repositories.category_repository import (
    CategoryRepository,
)
from ai_news_digest.infrastructure.database.repositories.topic_repository import (
    SqlAlchemyTopicRepository,
)
from ai_news_digest.workers.tasks import process

pytestmark = pytest.mark.integration


def _container_generator(container: Container):
    async def _gen() -> AsyncGenerator[Container, None]:
        yield container

    return _gen


def _make_source() -> Source:
    return Source(
        id=uuid4(),
        name=f"Tx Worker Source {uuid4().hex[:8]}",
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
        title="Worker Transaction Test Article",
        url=f"https://example.com/worker-tx/{uuid4()}",
        summary="Initial RSS summary.",
        content="Article body content used for deterministic processing.",
        source_id=source.id,
        published_at=datetime.now(UTC),
    )
    article.status = status
    return article


async def _article_status(session, article_id):
    result = await session.execute(
        text("SELECT status FROM articles WHERE id = :id"), {"id": str(article_id)}
    )
    row = result.scalar_one_or_none()
    return None if row is None else str(row)


async def _count_rows(session, model) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


class _FailingArticleRepository:
    def __init__(self, inner) -> None:
        self._inner = inner
        self.session = inner.session

    async def update_flush_only(self, article):
        raise RuntimeError("simulated article update failure")

    def __getattr__(self, item):
        return getattr(self._inner, item)


class _StubContainer:
    def __init__(self, session, article_repository) -> None:
        self.article_repository = article_repository
        self.category_repository = CategoryRepository(session)
        self.topic_repository = SqlAlchemyTopicRepository(session)
        self.summarize_article = None
        self.categorize_article = None
        self.process_article = None
        self.analyze_article = None
        self.analyze_and_materialize = None


# 1. NEW article -> successful deterministic summarization (commits).
async def test_summarize_new_article_commits(db_session, container) -> None:
    source = await container.source_repository.create(_make_source())
    article = await container.article_repository.create(_make_article(source))
    await db_session.commit()

    with patch.object(process, "get_container", _container_generator(container)):
        result = await process._summarize_article_impl(article.id)

    assert result == {
        "status": "completed",
        "article_id": str(article.id),
        "article_status": ArticleStatus.SUMMARIZED,
    }
    assert await _article_status(db_session, article.id) == ArticleStatus.SUMMARIZED.value


# 2. SUMMARIZED article -> successful deterministic categorization (commits).
async def test_categorize_summarized_article_commits(db_session, container) -> None:
    source = await container.source_repository.create(_make_source())
    article = await container.article_repository.create(
        _make_article(source, ArticleStatus.SUMMARIZED)
    )
    await db_session.commit()

    with patch.object(process, "get_container", _container_generator(container)):
        result = await process._categorize_article_impl(article.id)

    assert result["status"] == "completed"
    assert result["article_status"] == ArticleStatus.CATEGORIZED
    assert await _article_status(db_session, article.id) == ArticleStatus.CATEGORIZED.value
    assert await _count_rows(db_session, CategoryModel) == 1
    assert await _count_rows(db_session, TopicModel) == 1
    assert await _count_rows(db_session, ArticleTopicModel) == 1


# 3. Analyze entry point with a SELECT-triggered active transaction (no InvalidRequestError).
async def test_analyze_entry_point_no_invalid_request_error(db_session, container) -> None:
    source = await container.source_repository.create(_make_source())
    article = await container.article_repository.create(_make_article(source, ArticleStatus.NEW))
    await db_session.commit()

    with patch.object(process, "get_container", _container_generator(container)):
        result = await process._analyze_article_impl(article.id)

    assert result["status"] == "completed"
    assert result["article_status"] == ArticleStatus.ANALYZED
    assert await _article_status(db_session, article.id) == ArticleStatus.ANALYZED.value


# 4. Successful full processing persists all expected records after lifecycle completes.
async def test_process_article_persists_all_records(db_session, container) -> None:
    source = await container.source_repository.create(_make_source())
    article = await container.article_repository.create(_make_article(source))
    await db_session.commit()

    with patch.object(process, "get_container", _container_generator(container)):
        result = await process._process_article_impl(article.id)

    assert result["status"] == "completed"
    assert result["article_status"] == ArticleStatus.CATEGORIZED
    assert await _article_status(db_session, article.id) == ArticleStatus.CATEGORIZED.value
    assert await _count_rows(db_session, CategoryModel) == 1
    assert await _count_rows(db_session, TopicModel) == 1
    assert await _count_rows(db_session, ArticleTopicModel) == 1


# 5. Failure after category/topic/link operations rolls back everything.
async def test_process_article_rollback_on_update_failure(db_session) -> None:
    session_container = Container(db_session)
    failing_repo = _FailingArticleRepository(session_container.article_repository)
    stub = _StubContainer(db_session, failing_repo)

    source = await session_container.source_repository.create(_make_source())
    article = await session_container.article_repository.create(_make_article(source))
    await db_session.commit()

    with (
        patch.object(process, "get_container", _container_generator(stub)),
        pytest.raises(RuntimeError, match="simulated article update failure"),
    ):
        await process._process_article_impl(article.id)

    assert await _article_status(db_session, article.id) == ArticleStatus.NEW.value
    assert await _count_rows(db_session, CategoryModel) == 0
    assert await _count_rows(db_session, TopicModel) == 0
    assert await _count_rows(db_session, ArticleTopicModel) == 0


# 6. AI-enabled processing remains unaffected (use_case path commits normally).
async def test_ai_enabled_summarize_remains_unaffected(db_session) -> None:
    from ai_news_digest.application.ai.decision_engine import DecisionEngine
    from ai_news_digest.application.ai.provider_registry import ProviderRegistry
    from tests.e2e.test_pipeline_e2e import FakeAIProvider, _ai_enabled_settings

    fake_provider = FakeAIProvider()
    with _ai_enabled_settings():
        container = Container(db_session)
        container._free_only = False
        container._provider_registry = ProviderRegistry(free_only=False)
        container._provider_registry.register(fake_provider)
        container._capability_registry.register_provider("summarization", fake_provider.id)
        container._capability_registry.register_provider("categorization", fake_provider.id)
        container._decision_engine = DecisionEngine(
            container._provider_registry, container._capability_registry
        )

        source = await container.source_repository.create(_make_source())
        article = await container.article_repository.create(_make_article(source))
        await db_session.commit()

        with patch.object(process, "get_container", _container_generator(container)):
            result = await process._summarize_article_impl(article.id)

    assert result["status"] == "completed"
    assert result["article_status"] == ArticleStatus.SUMMARIZED
    assert await _article_status(db_session, article.id) == ArticleStatus.SUMMARIZED.value


# 7. Repeated execution remains idempotent.
async def test_deterministic_summarize_idempotent_repeat(db_session, container) -> None:
    source = await container.source_repository.create(_make_source())
    article = await container.article_repository.create(_make_article(source))
    await db_session.commit()

    with patch.object(process, "get_container", _container_generator(container)):
        first = await process._summarize_article_impl(article.id)
        second = await process._summarize_article_impl(article.id)

    assert first["status"] == "completed"
    assert first["article_status"] == ArticleStatus.SUMMARIZED
    assert second["status"] == "already_processed"
    assert await _article_status(db_session, article.id) == ArticleStatus.SUMMARIZED.value
