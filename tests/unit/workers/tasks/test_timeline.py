"""
Unit tests for story timeline generation Celery task.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from ai_news_digest.workers.tasks.timeline import generate_story_timeline
from tests.unit.workers.tasks.conftest import container_generator


class TestGenerateStoryTimelineTask:
    def test_disabled_returns_status(self) -> None:
        mock_container = MagicMock()

        with (
            patch(
                "ai_news_digest.workers.tasks.timeline.get_container",
                container_generator(mock_container),
            ),
            patch("ai_news_digest.workers.tasks.timeline.get_settings") as mock_settings,
        ):
            mock_settings.return_value.timeline_generation_enabled = False
            result = generate_story_timeline()

        assert result["status"] == "disabled"

    def test_empty_clusters_returns_completed(self) -> None:
        mock_container = MagicMock()
        cluster_repo = MagicMock()
        cluster_repo.find_recent_active_clusters = AsyncMock(return_value=[])
        mock_container.story_cluster_repository = cluster_repo
        use_case = MagicMock()
        use_case.execute = AsyncMock()
        mock_container.generate_story_timeline = use_case

        with (
            patch(
                "ai_news_digest.workers.tasks.timeline.get_container",
                container_generator(mock_container),
            ),
            patch("ai_news_digest.workers.tasks.timeline.get_settings") as mock_settings,
        ):
            mock_settings.return_value.timeline_generation_enabled = True
            mock_settings.return_value.timeline_lookback_days = 7
            mock_settings.return_value.max_story_candidates = 10
            result = generate_story_timeline()

        assert result["status"] == "completed"
        assert result["clusters_processed"] == 0
        assert result["total_events"] == 0

    def test_success_processes_clusters(self) -> None:
        cluster = SimpleNamespace(id="cluster-1")
        mock_container = MagicMock()
        cluster_repo = MagicMock()
        cluster_repo.find_recent_active_clusters = AsyncMock(return_value=[cluster])
        mock_container.story_cluster_repository = cluster_repo
        use_case = MagicMock()
        use_case.execute = AsyncMock(return_value={"events_created": 3})
        mock_container.generate_story_timeline = use_case

        with (
            patch(
                "ai_news_digest.workers.tasks.timeline.get_container",
                container_generator(mock_container),
            ),
            patch("ai_news_digest.workers.tasks.timeline.get_settings") as mock_settings,
        ):
            mock_settings.return_value.timeline_generation_enabled = True
            mock_settings.return_value.timeline_lookback_days = 7
            mock_settings.return_value.max_story_candidates = 10
            result = generate_story_timeline()

        assert result["status"] == "completed"
        assert result["clusters_processed"] == 1
        assert result["total_events"] == 3

    def test_cluster_failure_is_skipped(self) -> None:
        cluster = SimpleNamespace(id="cluster-1")
        mock_container = MagicMock()
        cluster_repo = MagicMock()
        cluster_repo.find_recent_active_clusters = AsyncMock(return_value=[cluster])
        mock_container.story_cluster_repository = cluster_repo
        use_case = MagicMock()
        use_case.execute = AsyncMock(side_effect=RuntimeError("boom"))
        mock_container.generate_story_timeline = use_case

        with (
            patch(
                "ai_news_digest.workers.tasks.timeline.get_container",
                container_generator(mock_container),
            ),
            patch("ai_news_digest.workers.tasks.timeline.get_settings") as mock_settings,
        ):
            mock_settings.return_value.timeline_generation_enabled = True
            mock_settings.return_value.timeline_lookback_days = 7
            mock_settings.return_value.max_story_candidates = 10
            result = generate_story_timeline()

        assert result["status"] == "completed"
        assert result["clusters_processed"] == 1
        assert result["total_events"] == 0

    def test_no_container_returns_not_found(self) -> None:
        async def empty_gen():
            for _ in ():
                yield _

        with (
            patch(
                "ai_news_digest.workers.tasks.timeline.get_container",
                lambda: empty_gen(),
            ),
            patch("ai_news_digest.workers.tasks.timeline.get_settings") as mock_settings,
        ):
            mock_settings.return_value.timeline_generation_enabled = True
            mock_settings.return_value.timeline_lookback_days = 7
            mock_settings.return_value.max_story_candidates = 10
            result = generate_story_timeline()

        assert result["status"] == "not_found"


__all__ = ["TestGenerateStoryTimelineTask"]
