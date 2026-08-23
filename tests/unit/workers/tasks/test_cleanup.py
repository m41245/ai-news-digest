"""
Unit tests for ``workers/tasks/cleanup.py``.

Covers ``cleanup_old_articles`` and ``cleanup_old_digests``. A deterministic
"now" is captured per test and threaded into the fixture objects so the cutoff
calculation is stable (no ``freezegun`` dependency required).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.article import Article
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.workers.celery_app import celery_app
from ai_news_digest.workers.tasks import cleanup
from tests.unit.workers.tasks.conftest import container_generator


def _article_at(age_days: int, now: datetime, status=ArticleStatus.NEW) -> Article:
    article = Article.create(
        title="Old Article",
        url="https://example.com/old",
        summary="s",
        content="c",
        source_id=uuid4(),
        published_at=now - timedelta(days=age_days),
    )
    article.status = status
    return article


def _digest_at(age_days: int, now: datetime) -> Digest:
    digest = Digest.create(
        title="Digest",
        content="c",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=[],
    )
    digest.generated_at = now - timedelta(days=age_days)
    return digest


async def test_cleanup_old_articles_deletes_stale_only(
    mock_container: MagicMock,
) -> None:
    """Only articles older than the cutoff are deleted."""
    # Arrange
    now = datetime.now(UTC)
    stale = _article_at(40, now)
    fresh = _article_at(5, now)
    mock_container.article_repository.list_recent.return_value = [stale, fresh]

    # Act
    with patch.object(cleanup, "get_container", container_generator(mock_container)):
        result = await cleanup.cleanup_old_articles(days=30)

    # Assert
    assert result == {"deleted": 1, "days": 30}
    mock_container.article_repository.list_recent.assert_awaited_once_with(limit=1000, offset=0)
    mock_container.article_repository.delete.assert_awaited_once_with(stale.id)


async def test_cleanup_old_articles_none_deleted(
    mock_container: MagicMock,
) -> None:
    """When everything is newer than the cutoff nothing is deleted."""
    # Arrange
    now = datetime.now(UTC)
    fresh = _article_at(5, now)
    mock_container.article_repository.list_recent.return_value = [fresh]

    # Act
    with patch.object(cleanup, "get_container", container_generator(mock_container)):
        result = await cleanup.cleanup_old_articles(days=30)

    # Assert
    assert result == {"deleted": 0, "days": 30}
    mock_container.article_repository.delete.assert_not_awaited()


async def test_cleanup_old_articles_empty_repository(
    mock_container: MagicMock,
) -> None:
    """An empty repository yields a zero deletion count."""
    # Arrange
    mock_container.article_repository.list_recent.return_value = []

    # Act
    with patch.object(cleanup, "get_container", container_generator(mock_container)):
        result = await cleanup.cleanup_old_articles(days=30)

    # Assert
    assert result == {"deleted": 0, "days": 30}


async def test_cleanup_old_articles_custom_days(
    mock_container: MagicMock,
) -> None:
    """The ``days`` argument controls both the cutoff and the result dict."""
    # Arrange
    now = datetime.now(UTC)
    stale = _article_at(15, now)
    mock_container.article_repository.list_recent.return_value = [stale]

    # Act
    with patch.object(cleanup, "get_container", container_generator(mock_container)):
        result = await cleanup.cleanup_old_articles(days=10)

    # Assert
    cutoff = now - timedelta(days=10)
    assert stale.published_at < cutoff
    assert result == {"deleted": 1, "days": 10}
    mock_container.article_repository.delete.assert_awaited_once_with(stale.id)


async def test_cleanup_old_articles_delete_error_propagates(
    mock_container: MagicMock,
) -> None:
    """A delete failure propagates (the task has no error handling)."""
    # Arrange
    now = datetime.now(UTC)
    stale = _article_at(40, now)
    mock_container.article_repository.list_recent.return_value = [stale]
    mock_container.article_repository.delete.side_effect = RuntimeError("boom")

    # Act / Assert
    with (
        patch.object(cleanup, "get_container", container_generator(mock_container)),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await cleanup.cleanup_old_articles(days=30)


async def test_cleanup_old_digests_deletes_stale_only(
    mock_container: MagicMock,
) -> None:
    """Only digests older than the cutoff are deleted."""
    # Arrange
    now = datetime.now(UTC)
    stale = _digest_at(120, now)
    fresh = _digest_at(5, now)
    mock_container.digest_repository.list_recent.return_value = [stale, fresh]

    # Act
    with patch.object(cleanup, "get_container", container_generator(mock_container)):
        result = await cleanup.cleanup_old_digests(days=90)

    # Assert
    assert result == {"deleted": 1, "days": 90}
    mock_container.digest_repository.list_recent.assert_awaited_once_with(limit=1000, offset=0)
    mock_container.digest_repository.delete.assert_awaited_once_with(stale.id)


async def test_cleanup_old_digests_none_deleted(
    mock_container: MagicMock,
) -> None:
    """When every digest is newer than the cutoff nothing is deleted."""
    # Arrange
    now = datetime.now(UTC)
    fresh = _digest_at(5, now)
    mock_container.digest_repository.list_recent.return_value = [fresh]

    # Act
    with patch.object(cleanup, "get_container", container_generator(mock_container)):
        result = await cleanup.cleanup_old_digests(days=90)

    # Assert
    assert result == {"deleted": 0, "days": 90}
    mock_container.digest_repository.delete.assert_not_awaited()


def test_cleanup_task_registration() -> None:
    """Both cleanup tasks are registered with the expected names and retries."""
    assert cleanup.cleanup_old_articles.name == "workers.tasks.cleanup.cleanup_old_articles"
    assert cleanup.cleanup_old_digests.name == "workers.tasks.cleanup.cleanup_old_digests"

    for task in (cleanup.cleanup_old_articles, cleanup.cleanup_old_digests):
        assert task.name in celery_app.tasks
        assert task.max_retries == 2
        assert task.default_retry_delay == 180
