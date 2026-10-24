"""
Unit tests for intelligence evaluation Celery task.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from ai_news_digest.workers.tasks.evaluation import (
    _run_intelligence_evaluation_impl as run_intelligence_evaluation,
)


class TestRunIntelligenceEvaluationTask:
    async def test_disabled_returns_skipped(self) -> None:
        with patch("ai_news_digest.workers.tasks.evaluation.get_settings") as mock_settings:
            mock_settings.return_value.evaluation_enabled = False
            result = await run_intelligence_evaluation()
        assert result["status"] == "skipped"

    async def test_success_returns_result(self) -> None:
        report = SimpleNamespace(
            run_id="run-1",
            status=SimpleNamespace(value="completed"),
            sample_count=5,
            metrics=[1, 2],
            error=None,
        )
        service = MagicMock()
        service.run_evaluation = AsyncMock(return_value=report)
        service.create_snapshot = MagicMock(return_value="snapshot")

        repo = MagicMock()
        repo.save_run = AsyncMock()
        repo.save_metrics = AsyncMock()
        repo.save_snapshot = AsyncMock()

        container = MagicMock()
        container.evaluation_repository = repo

        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("ai_news_digest.workers.tasks.evaluation.get_settings") as mock_settings,
            patch(
                "ai_news_digest.infrastructure.database.session.SessionLocal", return_value=session
            ),
            patch("ai_news_digest.bootstrap.container.Container", return_value=container),
            patch(
                "ai_news_digest.application.services.intelligence_evaluation_service.IntelligenceEvaluationService",
                return_value=service,
            ),
        ):
            mock_settings.return_value.evaluation_enabled = True
            result = await run_intelligence_evaluation()

        assert result["run_id"] == "run-1"
        assert result["status"] == "completed"
        assert result["sample_count"] == 5
        assert result["metric_count"] == 2

    async def test_persist_failure_is_suppressed(self) -> None:
        report = SimpleNamespace(
            run_id="run-1",
            status=SimpleNamespace(value="completed"),
            sample_count=5,
            metrics=[],
            error=None,
        )
        service = MagicMock()
        service.run_evaluation = AsyncMock(return_value=report)
        service.create_snapshot = MagicMock(return_value="snapshot")

        repo = MagicMock()
        repo.save_run = AsyncMock(side_effect=RuntimeError("db"))
        repo.save_metrics = AsyncMock()
        repo.save_snapshot = AsyncMock()

        container = MagicMock()
        container.evaluation_repository = repo

        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("ai_news_digest.workers.tasks.evaluation.get_settings") as mock_settings,
            patch(
                "ai_news_digest.infrastructure.database.session.SessionLocal", return_value=session
            ),
            patch("ai_news_digest.bootstrap.container.Container", return_value=container),
            patch(
                "ai_news_digest.application.services.intelligence_evaluation_service.IntelligenceEvaluationService",
                return_value=service,
            ),
        ):
            mock_settings.return_value.evaluation_enabled = True
            result = await run_intelligence_evaluation()

        assert result["status"] == "completed"


__all__ = ["TestRunIntelligenceEvaluationTask"]
