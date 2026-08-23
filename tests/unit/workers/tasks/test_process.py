"""
Unit tests for ``workers/tasks/process.py``.

Covers ``summarize_article``, ``categorize_article``, ``summarize_pending_articles``
and ``categorize_pending_articles``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.workers.celery_app import celery_app
from ai_news_digest.workers.tasks import process
from tests.unit.workers.tasks.conftest import (
    container_generator,
    make_article,
)

# ----------------------------------------------------------------------
# summarize_article
# ----------------------------------------------------------------------


async def test_summarize_article_not_found(mock_container: MagicMock) -> None:
    """When the article does not exist the task returns ``not_found``."""
    # Arrange
    article_id = uuid4()
    mock_container.article_repository.get_by_id.return_value = None

    # Act
    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.summarize_article(article_id)

    # Assert
    assert result == {"status": "not_found"}
    mock_container.article_repository.get_by_id.assert_awaited_once_with(article_id)
    mock_container.summarize_article.execute.assert_not_awaited()


async def test_summarize_article_already_processed(
    mock_container: MagicMock,
) -> None:
    """A non-NEW article is skipped without running the use case."""
    # Arrange
    article = make_article(ArticleStatus.SUMMARIZED)
    mock_container.article_repository.get_by_id.return_value = article

    # Act
    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.summarize_article(article.id)

    # Assert
    assert result == {"status": "already_processed"}
    mock_container.summarize_article.execute.assert_not_awaited()


async def test_summarize_article_completed(mock_container: MagicMock) -> None:
    """A NEW article is summarized and the completion dict is returned."""
    # Arrange
    article = make_article(ArticleStatus.NEW)
    updated = make_article(ArticleStatus.SUMMARIZED)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.summarize_article.execute.return_value = updated

    # Act
    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.summarize_article(article.id)

    # Assert
    assert result == {
        "status": "completed",
        "article_id": str(updated.id),
        "article_status": updated.status,
    }
    mock_container.summarize_article.execute.assert_awaited_once_with(article)


async def test_summarize_article_failure_propagates(
    mock_container: MagicMock,
) -> None:
    """A failing use case is re-raised by the task wrapper."""
    # Arrange
    article = make_article(ArticleStatus.NEW)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.summarize_article.execute.side_effect = RuntimeError("boom")

    # Act / Assert
    with (
        patch.object(process, "get_container", container_generator(mock_container)),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await process.summarize_article(article.id)


# ----------------------------------------------------------------------
# categorize_article
# ----------------------------------------------------------------------


async def test_categorize_article_not_found(mock_container: MagicMock) -> None:
    """When the article does not exist the task returns ``not_found``."""
    # Arrange
    article_id = uuid4()
    mock_container.article_repository.get_by_id.return_value = None

    # Act
    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.categorize_article(article_id)

    # Assert
    assert result == {"status": "not_found"}


async def test_categorize_article_not_ready(mock_container: MagicMock) -> None:
    """A non-SUMMARIZED article is skipped without running the use case."""
    # Arrange
    article = make_article(ArticleStatus.NEW)
    mock_container.article_repository.get_by_id.return_value = article

    # Act
    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.categorize_article(article.id)

    # Assert
    assert result == {"status": "not_ready"}
    mock_container.categorize_article.execute.assert_not_awaited()


async def test_categorize_article_completed(mock_container: MagicMock) -> None:
    """A SUMMARIZED article is categorized and the completion dict is returned."""
    # Arrange
    article = make_article(ArticleStatus.SUMMARIZED)
    updated = make_article(ArticleStatus.CATEGORIZED)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.categorize_article.execute.return_value = updated

    # Act
    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.categorize_article(article.id)

    # Assert
    assert result == {
        "status": "completed",
        "article_id": str(updated.id),
        "article_status": updated.status,
    }
    mock_container.categorize_article.execute.assert_awaited_once_with(article)


async def test_categorize_article_failure_propagates(
    mock_container: MagicMock,
) -> None:
    """A failing use case is re-raised by the task wrapper."""
    # Arrange
    article = make_article(ArticleStatus.SUMMARIZED)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.categorize_article.execute.side_effect = RuntimeError("boom")

    # Act / Assert
    with (
        patch.object(process, "get_container", container_generator(mock_container)),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await process.categorize_article(article.id)


# ----------------------------------------------------------------------
# summarize_pending_articles
# ----------------------------------------------------------------------


async def test_summarize_pending_articles_queues_new(
    mock_container: MagicMock,
) -> None:
    """Only NEW articles are queued via ``summarize_article.delay``."""
    # Arrange
    new = make_article(ArticleStatus.NEW)
    ready = make_article(ArticleStatus.READY)
    mock_container.article_repository.list_recent.return_value = [new, ready]

    # Act
    with (
        patch.object(process, "get_container", container_generator(mock_container)),
        patch.object(process, "summarize_article") as mock_task,
    ):
        result = await process.summarize_pending_articles()

    # Assert
    assert result == {"queued": 1}
    mock_container.article_repository.list_recent.assert_awaited_once_with(limit=100)
    mock_task.delay.assert_called_once_with(new.id)


async def test_summarize_pending_articles_none_queued(
    mock_container: MagicMock,
) -> None:
    """When there are no NEW articles, nothing is queued."""
    # Arrange
    ready = make_article(ArticleStatus.READY)
    mock_container.article_repository.list_recent.return_value = [ready]

    # Act
    with (
        patch.object(process, "get_container", container_generator(mock_container)),
        patch.object(process, "summarize_article") as mock_task,
    ):
        result = await process.summarize_pending_articles()

    # Assert
    assert result == {"processed": 0}
    mock_task.delay.assert_not_called()


async def test_summarize_pending_articles_failure_propagates(
    mock_container: MagicMock,
) -> None:
    """A repository error is re-raised by the task wrapper."""
    # Arrange
    mock_container.article_repository.list_recent.side_effect = RuntimeError("boom")

    # Act / Assert
    with (
        patch.object(process, "get_container", container_generator(mock_container)),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await process.summarize_pending_articles()


# ----------------------------------------------------------------------
# categorize_pending_articles
# ----------------------------------------------------------------------


async def test_categorize_pending_articles_queues_summarized(
    mock_container: MagicMock,
) -> None:
    """Only SUMMARIZED articles are queued via ``categorize_article.delay``."""
    # Arrange
    summarized = make_article(ArticleStatus.SUMMARIZED)
    new = make_article(ArticleStatus.NEW)
    mock_container.article_repository.list_recent.return_value = [summarized, new]

    # Act
    with (
        patch.object(process, "get_container", container_generator(mock_container)),
        patch.object(process, "categorize_article") as mock_task,
    ):
        result = await process.categorize_pending_articles()

    # Assert
    assert result == {"queued": 1}
    mock_container.article_repository.list_recent.assert_awaited_once_with(limit=100)
    mock_task.delay.assert_called_once_with(summarized.id)


async def test_categorize_pending_articles_none_queued(
    mock_container: MagicMock,
) -> None:
    """When there are no SUMMARIZED articles, nothing is queued."""
    # Arrange
    new = make_article(ArticleStatus.NEW)
    mock_container.article_repository.list_recent.return_value = [new]

    # Act
    with (
        patch.object(process, "get_container", container_generator(mock_container)),
        patch.object(process, "categorize_article") as mock_task,
    ):
        result = await process.categorize_pending_articles()

    # Assert
    assert result == {"processed": 0}
    mock_task.delay.assert_not_called()


# ----------------------------------------------------------------------
# process_article
# ----------------------------------------------------------------------


async def test_process_article_not_found(mock_container: MagicMock) -> None:
    """When the article does not exist the task returns ``not_found``."""
    article_id = uuid4()
    mock_container.article_repository.get_by_id.return_value = None

    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.process_article(article_id)

    assert result == {"status": "not_found"}


async def test_process_article_already_processed(mock_container: MagicMock) -> None:
    """A CATEGORIZED article is skipped without running the use case."""
    article = make_article(ArticleStatus.CATEGORIZED)
    mock_container.article_repository.get_by_id.return_value = article

    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.process_article(article.id)

    assert result == {"status": "already_processed"}
    mock_container.process_article.execute.assert_not_awaited()


async def test_process_article_completed(mock_container: MagicMock) -> None:
    """A NEW article is processed through the pipeline."""
    article = make_article(ArticleStatus.NEW)
    updated = make_article(ArticleStatus.CATEGORIZED)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.process_article.execute.return_value = updated

    with patch.object(process, "get_container", container_generator(mock_container)):
        result = await process.process_article(article.id)

    assert result == {
        "status": "completed",
        "article_id": str(updated.id),
        "article_status": updated.status,
    }
    mock_container.process_article.execute.assert_awaited_once_with(article)


async def test_process_article_failure_propagates(mock_container: MagicMock) -> None:
    """A failing use case is re-raised by the task wrapper."""
    article = make_article(ArticleStatus.NEW)
    mock_container.article_repository.get_by_id.return_value = article
    mock_container.process_article.execute.side_effect = RuntimeError("boom")

    with (
        patch.object(process, "get_container", container_generator(mock_container)),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await process.process_article(article.id)


# ----------------------------------------------------------------------
# Registration
# ----------------------------------------------------------------------


def test_process_task_registration() -> None:
    """All process tasks are registered with the expected names and retries."""
    assert process.summarize_article.name == "workers.tasks.process.summarize_article"
    assert process.categorize_article.name == "workers.tasks.process.categorize_article"
    assert process.process_article.name == "workers.tasks.process.process_article"
    assert (
        process.summarize_pending_articles.name
        == "workers.tasks.process.summarize_pending_articles"
    )
    assert (
        process.categorize_pending_articles.name
        == "workers.tasks.process.categorize_pending_articles"
    )

    for task in (
        process.summarize_article,
        process.categorize_article,
        process.process_article,
    ):
        assert task.name in celery_app.tasks
        assert task.max_retries == 3
        assert task.default_retry_delay == 120

    for task in (
        process.summarize_pending_articles,
        process.categorize_pending_articles,
    ):
        assert task.name in celery_app.tasks
