"""
Unit tests for ``workers/tasks/ranking.py`` (``rank_stories``).

All repositories, settings, and task dependencies are mocked so the task runs
without a real database, Redis, broker, or external services. The ranking
engine and top-story selector are task-level dependencies instantiated inside
the implementation, so they are patched at module level.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.workers.celery_app import celery_app
from ai_news_digest.workers.tasks import ranking
from tests.unit.workers.tasks.conftest import container_generator


def _settings(story_ranking_enabled: bool = True) -> MagicMock:
    settings = MagicMock()
    settings.story_ranking_enabled = story_ranking_enabled
    settings.ranking_lookback_hours = 24
    settings.ranking_max_candidates = 50
    settings.ranking_recency_weight = 1.0
    settings.ranking_source_trust_weight = 1.0
    settings.ranking_source_diversity_weight = 1.0
    settings.ranking_corroboration_weight = 1.0
    settings.ranking_company_relevance_weight = 1.0
    settings.ranking_category_topic_relevance_weight = 1.0
    settings.ranking_article_quality_weight = 1.0
    settings.ranking_official_announcement_weight = 1.0
    settings.ranking_recency_decay_hours = 24.0
    return settings


def _configure_container(mock_container: MagicMock, clusters) -> None:
    mock_container.story_cluster_repository = MagicMock()
    mock_container.story_cluster_repository.find_recent_active_clusters = AsyncMock(
        return_value=clusters
    )
    mock_container.story_cluster_repository.bulk_update_ranking = AsyncMock()
    mock_container.source_repository = MagicMock()
    mock_container.source_repository.list_all = AsyncMock(return_value=[])
    mock_container.category_repository = MagicMock()
    mock_container.category_repository.list_all = AsyncMock(return_value=[])
    mock_container.company_repository = MagicMock()
    mock_container.company_repository.list_all = AsyncMock(return_value=[])
    mock_container.topic_repository = MagicMock()
    mock_container.topic_repository.list_all = AsyncMock(return_value=[])
    mock_container.article_repository = MagicMock()
    mock_container.article_repository.list_by_cluster_id = AsyncMock(return_value=[])


async def test_ranking_disabled(mock_container: MagicMock) -> None:
    """Ranking disabled returns ``skipped`` before touching any repository."""
    with (
        patch.object(ranking, "get_settings", return_value=_settings(False)),
        patch.object(ranking, "get_container", container_generator(mock_container)),
    ):
        result = await ranking.rank_stories()

    assert result == {"status": "skipped", "reason": "ranking_disabled"}


async def test_no_eligible_clusters(mock_container: MagicMock) -> None:
    """No active clusters returns ``completed`` with zero ranked clusters."""
    _configure_container(mock_container, clusters=[])
    settings = _settings()

    with (
        patch.object(ranking, "get_settings", return_value=settings),
        patch.object(ranking, "get_container", container_generator(mock_container)),
    ):
        result = await ranking.rank_stories()

    assert result == {
        "status": "completed",
        "ranked_clusters": "0",
        "top_story_cluster_id": "",
    }
    mock_container.story_cluster_repository.bulk_update_ranking.assert_not_awaited()


async def test_no_container_generator(mock_container: MagicMock) -> None:
    """An empty container generator returns ``skipped`` with reason ``no_container``."""

    async def empty_gen():  # pragma: no cover - zero-yield async generator
        if False:
            yield  # pragma: no cover

    settings = _settings()
    with (
        patch.object(ranking, "get_settings", return_value=settings),
        patch.object(ranking, "get_container", empty_gen),
    ):
        result = await ranking.rank_stories()

    assert result == {"status": "skipped", "reason": "no_container"}


async def test_no_bulk_update_when_no_ranking_updates(
    mock_container: MagicMock,
) -> None:
    """No ranking updates means ``bulk_update_ranking`` is not called."""
    _configure_container(mock_container, clusters=[MagicMock()])
    settings = _settings()

    top_story = MagicMock(top_story_cluster_id=None, top_story_score=None)
    selector_mock = MagicMock()
    selector_mock.rank_and_select.return_value = ([], top_story)

    with (
        patch.object(ranking, "get_settings", return_value=settings),
        patch.object(ranking, "get_container", container_generator(mock_container)),
        patch.object(ranking, "StoryRankingEngine"),
        patch.object(ranking, "TopStorySelector", return_value=selector_mock),
        patch.object(ranking, "record_celery_task_success", new=AsyncMock()),
        patch.object(ranking, "record_celery_task_failure", new=AsyncMock()),
        patch.object(ranking, "record_celery_task_duration", new=AsyncMock()),
    ):
        result = await ranking.rank_stories()

    assert result["status"] == "completed"
    assert result["ranked_clusters"] == "0"
    mock_container.story_cluster_repository.bulk_update_ranking.assert_not_awaited()


async def test_ranking_exception_records_failure_and_re_raises(
    mock_container: MagicMock,
) -> None:
    """A ranking failure is logged, recorded as a task failure, and re-raised."""
    _configure_container(mock_container, clusters=[])
    settings = _settings()
    mock_container.story_cluster_repository.find_recent_active_clusters.side_effect = RuntimeError(
        "boom"
    )

    with (
        patch.object(ranking, "get_settings", return_value=settings),
        patch.object(ranking, "get_container", container_generator(mock_container)),
        patch.object(ranking, "record_celery_task_success", new=AsyncMock()) as mock_success,
        patch.object(ranking, "record_celery_task_failure", new=AsyncMock()) as mock_failure,
        patch.object(ranking, "record_celery_task_duration", new=AsyncMock()) as mock_duration,
        pytest.raises(RuntimeError, match="boom"),
    ):
        await ranking.rank_stories()

    mock_failure.assert_called_once()
    mock_success.assert_not_called()
    mock_duration.assert_called_once()


async def test_successful_ranking_with_bulk_update(mock_container: MagicMock) -> None:
    """Successful ranking persists ranking updates via a bulk update."""
    _configure_container(mock_container, clusters=[MagicMock()])
    settings = _settings()

    cluster_id = str(uuid4())
    cluster = MagicMock(id=cluster_id)
    mock_container.story_cluster_repository.find_recent_active_clusters.return_value = [cluster]
    mock_container.article_repository.list_by_cluster_id.return_value = [MagicMock()]

    ranked = MagicMock()
    ranked.cluster = MagicMock(id=cluster_id)
    ranked.score = 0.92
    ranked.signals = [MagicMock(explanation="Recent story"), MagicMock(explanation=None)]
    top_story = MagicMock(top_story_cluster_id=cluster_id, top_story_score=0.92)

    selector_mock = MagicMock()
    selector_mock.rank_and_select.return_value = ([ranked], top_story)

    with (
        patch.object(ranking, "get_settings", return_value=settings),
        patch.object(ranking, "get_container", container_generator(mock_container)),
        patch.object(ranking, "StoryRankingEngine"),
        patch.object(ranking, "TopStorySelector", return_value=selector_mock),
        patch.object(ranking, "record_celery_task_success", new=AsyncMock()),
        patch.object(ranking, "record_celery_task_failure", new=AsyncMock()),
        patch.object(ranking, "record_celery_task_duration", new=AsyncMock()),
    ):
        result = await ranking.rank_stories()

    mock_container.story_cluster_repository.bulk_update_ranking.assert_awaited_once_with(
        [(cluster_id, 0.92, "Recent story")]
    )
    assert result["status"] == "completed"
    assert result["ranked_clusters"] == "1"
    assert result["top_story_cluster_id"] == cluster_id
    assert result["top_story_score"] == "0.92"


def test_rank_task_registration() -> None:
    """The task is registered with the expected name and retry settings."""
    assert ranking.rank_stories.name == "workers.tasks.ranking.rank_stories"
    assert ranking.rank_stories.name in celery_app.tasks
    assert ranking.rank_stories.max_retries == 3
    assert ranking.rank_stories.default_retry_delay == 60
