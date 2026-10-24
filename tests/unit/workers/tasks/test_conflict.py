"""
Unit tests for claim conflict detection Celery task.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from ai_news_digest.workers.tasks.conflict import detect_claim_conflicts
from tests.unit.workers.tasks.conftest import container_generator


class TestDetectClaimConflictsTask:
    def test_disabled_returns_status(self) -> None:
        mock_container = MagicMock()
        mock_container.detect_claim_conflicts = None

        with (
            patch(
                "ai_news_digest.workers.tasks.conflict.get_container",
                container_generator(mock_container),
            ),
            patch("ai_news_digest.workers.tasks.conflict.get_settings") as mock_settings,
        ):
            mock_settings.return_value.conflict_detection_enabled = False
            result = detect_claim_conflicts()

        assert result["status"] == "disabled"

    def test_use_case_unavailable_returns_status(self) -> None:
        mock_container = MagicMock()
        mock_container.detect_claim_conflicts = None

        with (
            patch(
                "ai_news_digest.workers.tasks.conflict.get_container",
                container_generator(mock_container),
            ),
            patch("ai_news_digest.workers.tasks.conflict.get_settings") as mock_settings,
        ):
            mock_settings.return_value.conflict_detection_enabled = True
            result = detect_claim_conflicts()

        assert result["status"] == "unavailable"

    def test_success_returns_result(self) -> None:
        mock_container = MagicMock()
        use_case = MagicMock()
        use_case.execute = AsyncMock(return_value={"candidates": 2, "conflicts": 1})
        mock_container.detect_claim_conflicts = use_case

        with (
            patch(
                "ai_news_digest.workers.tasks.conflict.get_container",
                container_generator(mock_container),
            ),
            patch("ai_news_digest.workers.tasks.conflict.get_settings") as mock_settings,
        ):
            mock_settings.return_value.conflict_detection_enabled = True
            result = detect_claim_conflicts()

        assert result["candidates"] == 2
        assert result["conflicts"] == 1

    def test_no_container_returns_not_found(self) -> None:
        async def empty_gen():
            for _ in ():
                yield _

        with (
            patch(
                "ai_news_digest.workers.tasks.conflict.get_container",
                lambda: empty_gen(),
            ),
            patch("ai_news_digest.workers.tasks.conflict.get_settings") as mock_settings,
        ):
            mock_settings.return_value.conflict_detection_enabled = True
            result = detect_claim_conflicts()

        assert result["status"] == "not_found"


__all__ = ["TestDetectClaimConflictsTask"]
