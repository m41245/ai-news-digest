"""
Unit tests for M85 trend detection Celery task.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ai_news_digest.workers.tasks.trend import detect_trends
from tests.unit.workers.tasks.conftest import container_generator


class TestDetectTrendsTask:
    def test_disabled_returns_status(self) -> None:
        mock_container = MagicMock()
        mock_container.detect_trends = None

        with patch(
            "ai_news_digest.workers.tasks.trend.get_container",
            container_generator(mock_container),
        ), patch(
            "ai_news_digest.workers.tasks.trend.get_settings"
        ) as mock_settings:
            mock_settings.return_value.trend_detection_enabled = False
            result = detect_trends()

        assert result["status"] == "disabled"

    def test_use_case_unavailable_returns_status(self) -> None:
        mock_container = MagicMock()
        mock_container.detect_trends = None

        with patch(
            "ai_news_digest.workers.tasks.trend.get_container",
            container_generator(mock_container),
        ), patch(
            "ai_news_digest.workers.tasks.trend.get_settings"
        ) as mock_settings:
            mock_settings.return_value.trend_detection_enabled = True
            result = detect_trends()

        assert result["status"] == "not_found"


__all__ = ["TestDetectTrendsTask"]
