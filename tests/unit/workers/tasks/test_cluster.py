"""
Unit tests for ``workers/tasks/cluster.py``.

Covers ``cluster_article`` and ``cluster_pending_articles``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.workers.celery_app import celery_app
from ai_news_digest.workers.tasks import cluster
from tests.unit.workers.tasks.conftest import (
    container_generator,
    make_article,
)


async def test_cluster_article_not_found(mock_container: MagicMock) -> None:
    article_id = uuid4()
    mock_container.article_repository.get_by_id.return_value = None

    with patch.object(cluster, "get_container", container_generator(mock_container)):
        result = await cluster.cluster_article(article_id)

    assert result == {"status": "not_found"}
    mock_container.article_repository.get_by_id.assert_awaited_once_with(article_id)


async def test_cluster_article_already_clustered(mock_container: MagicMock) -> None:
    article = make_article(ArticleStatus.READY)
    article.cluster_id = uuid4()
    mock_container.article_repository.get_by_id.return_value = article

    with patch.object(cluster, "get_container", container_generator(mock_container)):
        result = await cluster.cluster_article(article.id)

    assert result == {"status": "already_clustered"}
    mock_container.cluster_articles.execute.assert_not_awaited()


async def test_cluster_article_not_ready(mock_container: MagicMock) -> None:
    article = make_article(ArticleStatus.NEW)
    mock_container.article_repository.get_by_id.return_value = article

    with patch.object(cluster, "get_container", container_generator(mock_container)):
        result = await cluster.cluster_article(article.id)

    assert result == {"status": "not_ready"}
    mock_container.cluster_articles.execute.assert_not_awaited()


async def test_cluster_article_created_new_cluster(mock_container: MagicMock) -> None:
    article = make_article(ArticleStatus.CATEGORIZED)
    new_cluster = MagicMock()
    new_cluster.id = uuid4()
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.cluster_articles.execute.return_value = None

    with patch.object(cluster, "get_container", container_generator(mock_container)):
        result = await cluster.cluster_article(article.id)

    assert result["status"] == "created"
    mock_container.cluster_articles.execute.assert_awaited_once_with(article)


async def test_cluster_article_assigned_to_existing(mock_container: MagicMock) -> None:
    article = make_article(ArticleStatus.CATEGORIZED)
    existing_cluster = MagicMock()
    existing_cluster.id = uuid4()
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.cluster_articles.execute.return_value = existing_cluster

    with patch.object(cluster, "get_container", container_generator(mock_container)):
        result = await cluster.cluster_article(article.id)

    assert result == {
        "status": "assigned",
        "article_id": str(article.id),
        "cluster_id": str(existing_cluster.id),
    }
    mock_container.cluster_articles.execute.assert_awaited_once_with(article)


async def test_cluster_article_failure_propagates(mock_container: MagicMock) -> None:
    article = make_article(ArticleStatus.CATEGORIZED)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.cluster_articles.execute.side_effect = RuntimeError("boom")

    with (
        patch.object(cluster, "get_container", container_generator(mock_container)),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await cluster.cluster_article(article.id)


async def test_cluster_pending_articles_queues_new(
    mock_container: MagicMock,
) -> None:
    categorized = make_article(ArticleStatus.CATEGORIZED)
    analyzed = make_article(ArticleStatus.ANALYZED)
    ready = make_article(ArticleStatus.READY)
    mock_container.article_repository.list_by_status.side_effect = lambda s, limit: (
        [categorized] if s == ArticleStatus.CATEGORIZED else
        [analyzed] if s == ArticleStatus.ANALYZED else
        [ready] if s == ArticleStatus.READY else
        []
    )

    with (
        patch.object(cluster, "get_container", container_generator(mock_container)),
        patch.object(cluster, "cluster_article") as mock_task,
    ):
        result = await cluster.cluster_pending_articles()

    assert result["queued"] == 3
    assert mock_task.delay.call_count == 3


async def test_cluster_pending_articles_none_queued(
    mock_container: MagicMock,
) -> None:
    mock_container.article_repository.list_by_status.return_value = []

    with (
        patch.object(cluster, "get_container", container_generator(mock_container)),
        patch.object(cluster, "cluster_article") as mock_task,
    ):
        result = await cluster.cluster_pending_articles()

    assert result["queued"] == 0
    mock_task.delay.assert_not_called()


async def test_cluster_pending_articles_failure_propagates(
    mock_container: MagicMock,
) -> None:
    mock_container.article_repository.list_by_status.side_effect = RuntimeError("boom")

    with (
        patch.object(cluster, "get_container", container_generator(mock_container)),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await cluster.cluster_pending_articles()


def test_cluster_task_registration() -> None:
    assert cluster.cluster_article.name == "workers.tasks.cluster.cluster_article"
    assert (
        cluster.cluster_pending_articles.name
        == "workers.tasks.cluster.cluster_pending_articles"
    )

    for task in (
        cluster.cluster_article,
        cluster.cluster_pending_articles,
    ):
        assert task.name in celery_app.tasks
        assert task.max_retries == 3
        assert task.default_retry_delay == 60
