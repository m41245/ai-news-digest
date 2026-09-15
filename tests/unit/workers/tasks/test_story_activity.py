"""
Unit tests for M83 story activity Celery task.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ai_news_digest.workers.tasks.story_activity import detect_story_activity
from tests.unit.workers.tasks.conftest import container_generator


class TestDetectStoryActivityTask:
    def test_disabled_returns_status(self) -> None:
        mock_container = MagicMock()
        mock_container.detect_story_activity = None

        with patch(
            "ai_news_digest.workers.tasks.story_activity.get_container",
            container_generator(mock_container),
        ), patch(
            "ai_news_digest.workers.tasks.story_activity.get_settings"
        ) as mock_settings:
            mock_settings.return_value.breaking_detection_enabled = False
            result = detect_story_activity()

        assert result["status"] == "disabled"

    def test_use_case_unavailable_returns_status(self) -> None:
        mock_container = MagicMock()
        mock_container.detect_story_activity = None

        with patch(
            "ai_news_digest.workers.tasks.story_activity.get_container",
            container_generator(mock_container),
        ), patch(
            "ai_news_digest.workers.tasks.story_activity.get_settings"
        ) as mock_settings:
            mock_settings.return_value.breaking_detection_enabled = True
            result = detect_story_activity()

        assert result["status"] == "unavailable"


__all__ = ["TestDetectStoryActivityTask"]
