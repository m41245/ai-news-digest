"""
Shared fixtures and helpers for unit tests of the ``workers/tasks`` Celery tasks.

The task modules obtain their dependencies from a dependency-injection
``Container`` produced by ``get_container()``:

    async for container in get_container():
        ...

Tests patch the module-level ``get_container`` symbol of each task module with
``container_generator`` so the task logic runs against a mock container without
touching a real database, broker, or external services.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.digest import Digest


def container_generator(container: MagicMock):
    """
    Build a zero-arg async generator yielding a single mock ``Container``.

    Usage::

        with patch.object(module, "get_container", container_generator(mock_container)):
            ...
    """

    async def _gen() -> AsyncGenerator[MagicMock, None]:
        yield container

    return _gen


@pytest.fixture
def mock_container() -> MagicMock:
    """
    A ``Container`` double.

    Every repository and use case is an ``AsyncMock`` so tasks can be driven
    without a database. The container itself is a plain ``MagicMock`` so the
    task code can read attributes such as ``container.article_repository``.
    """
    container = MagicMock()

    for name in (
        "article_repository",
        "digest_repository",
        "delivery_repository",
        "source_repository",
        "ingest_all_sources",
        "summarize_article",
        "categorize_article",
        "process_article",
        "generate_digest",
        "deliver_digest",
    ):
        setattr(container, name, AsyncMock())

    return container


def make_article(status: ArticleStatus, age_days: int = 0) -> Article:
    """Create a real ``Article`` with the given status and publication age."""
    article = Article.create(
        title="Test Article",
        url=f"https://example.com/{uuid4()}",
        summary="A summary for testing.",
        content="Article body content.",
        source_id=uuid4(),
        published_at=datetime.now(UTC) - timedelta(days=age_days),
    )
    article.status = status
    return article


def make_digest(content: str = "Para one.\n\nPara two.") -> Digest:
    """Create a real ``Digest`` suitable for delivery tests."""
    return Digest.create(
        title="AI News Digest - 2026-01-01",
        content=content,
        digest_format=DigestFormat.MARKDOWN,
        article_ids=[uuid4()],
    )
