"""
Unit tests for ``workers/tasks/ingest.py`` (``fetch_all_sources``).
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest

from ai_news_digest.application.use_cases.article.ingest_all_sources import (
    IngestionSummary,
)
from ai_news_digest.workers.celery_app import celery_app
from ai_news_digest.workers.tasks import ingest
from tests.unit.workers.tasks.conftest import container_generator


async def test_fetch_all_sources_success(mock_container: MagicMock) -> None:
    """A successful run returns the ingestion counts as a dict."""
    # Arrange
    mock_container.ingest_all_sources.execute.return_value = IngestionSummary(
        sources_processed=2,
        fetched=10,
        imported=7,
        skipped=3,
    )

    # Act
    with patch.object(ingest, "get_container", container_generator(mock_container)):
        result = await ingest.fetch_all_sources()

    # Assert
    assert result == {
        "sources_processed": 2,
        "fetched": 10,
        "imported": 7,
        "skipped": 3,
    }
    mock_container.ingest_all_sources.execute.assert_awaited_once()


async def test_fetch_all_sources_zero_sources(mock_container: MagicMock) -> None:
    """When no sources are processed, all counts are zero."""
    # Arrange
    mock_container.ingest_all_sources.execute.return_value = IngestionSummary(
        sources_processed=0,
        fetched=0,
        imported=0,
        skipped=0,
    )

    # Act
    with patch.object(ingest, "get_container", container_generator(mock_container)):
        result = await ingest.fetch_all_sources()

    # Assert
    assert result == {
        "sources_processed": 0,
        "fetched": 0,
        "imported": 0,
        "skipped": 0,
    }


async def test_fetch_all_sources_failure_propagates(
    mock_container: MagicMock,
) -> None:
    """A failing use case is re-raised by the task wrapper."""
    # Arrange
    mock_container.ingest_all_sources.execute.side_effect = RuntimeError("boom")

    # Act / Assert
    with (
        patch.object(ingest, "get_container", container_generator(mock_container)),
        pytest.raises(RuntimeError, match="boom"),
    ):
        await ingest.fetch_all_sources()


def test_fetch_all_sources_registration() -> None:
    """The task is registered on the Celery app with the expected metadata."""
    assert ingest.fetch_all_sources.name == "workers.tasks.ingest.fetch_all_sources"
    assert ingest.fetch_all_sources.name in celery_app.tasks
    assert ingest.fetch_all_sources.max_retries == 3
    assert ingest.fetch_all_sources.default_retry_delay == 60


async def test_fetch_all_sources_apply_returns_coroutine(
    mock_container: MagicMock,
) -> None:
    """
    Regression guard: under Celery 5.x an ``async def`` task body is not awaited
    by ``apply()``, so ``result.result`` is an un-awaited coroutine. Tests must
    ``await`` the task object directly instead of asserting on ``apply()``.
    """
    # Arrange
    mock_container.ingest_all_sources.execute.return_value = IngestionSummary(
        sources_processed=1,
        fetched=1,
        imported=1,
        skipped=0,
    )

    # Act
    with patch.object(ingest, "get_container", container_generator(mock_container)):
        eager_result = ingest.fetch_all_sources.apply()

    # Assert
    assert not isinstance(eager_result.result, dict)
    assert inspect.iscoroutine(eager_result.result)
    # Clean up the un-awaited coroutine to avoid "never awaited" warnings.
    eager_result.result.close()
