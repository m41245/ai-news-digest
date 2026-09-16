"""Tests for M94 operational alert service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_news_digest.application.services.operational_alert_service import (
    OperationalAlertService,
)
from ai_news_digest.domain.evaluation.quality_gates import (
    AlertSeverity,
    IntelligenceComponent,
)


class TestOperationalAlertService:
    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        repo = MagicMock()
        repo.find_alert_by_deduplication_key = AsyncMock(return_value=None)
        repo.save_alert = AsyncMock()
        return repo

    @pytest.fixture
    def service(
        self, mock_repo: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> OperationalAlertService:
        monkeypatch.setattr(
            "ai_news_digest.application.services.operational_alert_service.get_settings",
            lambda: MagicMock(quality_gates_enabled=True),
        )
        return OperationalAlertService(alert_repository=mock_repo)

    def test_maybe_create_alert_creates_when_no_duplicate(
        self, service: OperationalAlertService, mock_repo: MagicMock
    ) -> None:
        mock_repo.find_alert_by_deduplication_key.return_value = None

        async def _run() -> None:
            alert = await service.maybe_create_alert(
                severity=AlertSeverity.CRITICAL,
                component=IntelligenceComponent.EXTRACTION,
                gate_id="extraction-success-rate",
                message="Extraction degraded",
                details={"current_value": 0.5},
            )
            assert alert is not None
            assert alert.severity == AlertSeverity.CRITICAL
            assert alert.component == IntelligenceComponent.EXTRACTION
            mock_repo.save_alert.assert_called_once()

        import asyncio
        asyncio.run(_run())

    def test_maybe_create_alert_skips_duplicate(
        self, service: OperationalAlertService, mock_repo: MagicMock
    ) -> None:
        existing = MagicMock()
        existing.alert_id = "alert-existing"
        mock_repo.find_alert_by_deduplication_key.return_value = existing

        async def _run() -> None:
            alert = await service.maybe_create_alert(
                severity=AlertSeverity.CRITICAL,
                component=IntelligenceComponent.EXTRACTION,
                gate_id="extraction-success-rate",
                message="Extraction degraded",
            )
            assert alert is None
            mock_repo.save_alert.assert_not_called()

        import asyncio
        asyncio.run(_run())

    def test_maybe_create_alert_skips_when_disabled(
        self, mock_repo: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "ai_news_digest.application.services.operational_alert_service.get_settings",
            lambda: MagicMock(quality_gates_enabled=False),
        )
        service = OperationalAlertService(alert_repository=mock_repo)

        async def _run() -> None:
            alert = await service.maybe_create_alert(
                severity=AlertSeverity.CRITICAL,
                component=IntelligenceComponent.EXTRACTION,
                gate_id="extraction-success-rate",
                message="Extraction degraded",
            )
            assert alert is None
            mock_repo.save_alert.assert_not_called()

        import asyncio
        asyncio.run(_run())

    def test_resolve_alerts_for_component(self, mock_repo: MagicMock) -> None:
        mock_repo.list_alerts = AsyncMock(
            return_value=(
                [
                    MagicMock(
                        alert_id="alert-1",
                        gate_id="extraction-success-rate",
                        resolved=False,
                    )
                ],
                1,
            )
        )
        mock_repo.resolve_alert = AsyncMock()
        service = OperationalAlertService(alert_repository=mock_repo)

        async def _run() -> None:
            count = await service.resolve_alerts_for_component(
                component=IntelligenceComponent.EXTRACTION,
                gate_id="extraction-success-rate",
            )
            assert count == 1
            mock_repo.resolve_alert.assert_called_once_with("alert-1")

        import asyncio
        asyncio.run(_run())


__all__ = ["TestOperationalAlertService"]
