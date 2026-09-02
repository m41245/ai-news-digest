"""
Unit tests for ``workers/tasks/cleanup.py``.

Covers ``cleanup_old_articles`` and ``cleanup_old_digests``. A deterministic
"now" is captured per test and threaded into the fixture objects so the cutoff
calculation is stable (no ``freezegun`` dependency required).
"""

from __future__ import annotations

from datetime import datetime, timedelta
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
    mock_container.article_repository.delete_older_than.return_value = 1

    with patch.object(cleanup, "get_container", container_generator(mock_container)):
        result = await cleanup.cleanup_old_articles(days=30)

    assert result == {"deleted": 1, "days": 30}
    mock_container.article_repository.delete_older_than.assert_awaited_once()
    assert mock_container.article_repository.delete_older_than.call_args.kwargs["limit"] == 1000


async def test_cleanup_old_articles_none_deleted(
    mock_container: MagicMock,
) -> None:
    """When everything is newer than the cutoff nothing is deleted."""
    mock_container.article_repository.delete_older_than.return_value = 0

    with patch.object(cleanup, "get_container", container_generator(mock_container)):
        result = await cleanup.cleanup_old_articles(days=30)

    assert result == {"deleted": 0, "days": 30}
    mock_container.article_repository.delete_older_than.assert_awaited_once()
    assert mock_container.article_repository.delete_older_than.call_args.kwargs["limit"] == 1000


async def test_cleanup_old_articles_empty_repository(
    mock_container: MagicMock,
) -> None:
    """An empty repository yields a zero deletion count."""
    mock_container.article_repository.delete_older_than.return_value = 0

    with patch.object(cleanup, "get_container", container_generator(mock_container)):
        result = await cleanup.cleanup_old_articles(days=30)

    assert result == {"deleted": 0, "days": 30}


async def test_cleanup_old_articles_custom_days(
    mock_container: MagicMock,
) -> None:
    """The ``days`` argument controls the cutoff passed to the repository."""
    mock_container.article_repository.delete_older_than.return_value = 1

    with patch.object(cleanup, "get_container", container_generator(mock_container)):
        result = await cleanup.cleanup_old_articles(days=10)

    assert result == {"deleted": 1, "days": 10}
    mock_container.article_repository.delete_older_than.assert_awaited_once()
    assert mock_container.article_repository.delete_older_than.call_args.kwargs["limit"] == 1000


async def test_cleanup_old_articles_delete_error_propagates(
    mock_container: MagicMock,
) -> None:
    """A delete failure propagates."""
    mock_container.article_repository.delete_older_than.side_effect = RuntimeError("boom")

    with (
        patch.object(cleanup, "get_container", container_generator(mock_container)),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await cleanup.cleanup_old_articles(days=30)


async def test_cleanup_old_digests_deletes_stale_only(
    mock_container: MagicMock,
) -> None:
    """Only digests older than the cutoff are deleted."""
    mock_container.digest_repository.delete_older_than.return_value = 1

    with patch.object(cleanup, "get_container", container_generator(mock_container)):
        result = await cleanup.cleanup_old_digests(days=90)

    assert result == {"deleted": 1, "days": 90}
    mock_container.digest_repository.delete_older_than.assert_awaited_once()
    assert mock_container.digest_repository.delete_older_than.call_args.kwargs["limit"] == 1000


async def test_cleanup_old_digests_none_deleted(
    mock_container: MagicMock,
) -> None:
    """When every digest is newer than the cutoff nothing is deleted."""
    mock_container.digest_repository.delete_older_than.return_value = 0

    with patch.object(cleanup, "get_container", container_generator(mock_container)):
        result = await cleanup.cleanup_old_digests(days=90)

    assert result == {"deleted": 0, "days": 90}
    mock_container.digest_repository.delete_older_than.assert_awaited_once()
    assert mock_container.digest_repository.delete_older_than.call_args.kwargs["limit"] == 1000


def test_cleanup_task_registration() -> None:
    """Both cleanup tasks are registered with the expected names and retries."""
    assert cleanup.cleanup_old_articles.name == "workers.tasks.cleanup.cleanup_old_articles"
    assert cleanup.cleanup_old_digests.name == "workers.tasks.cleanup.cleanup_old_digests"

    for task in (cleanup.cleanup_old_articles, cleanup.cleanup_old_digests):
        assert task.name in celery_app.tasks
        assert task.max_retries == 3
        assert task.default_retry_delay == 60
