"""
Operational alert management for M94.

Provides bounded alert creation, deduplication, and resolution.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.evaluation.quality_gates import (
    AlertSeverity,
    IntelligenceComponent,
    OperationalAlert,
)

logger = get_logger(__name__)


class OperationalAlertService:
    """Bounded operational alert management.

    Handles alert creation, deduplication, and resolution.
    Alerts are persisted with bounded retention.
    """

    def __init__(self, alert_repository: Any) -> None:
        self._settings = get_settings()
        self._alert_repository = alert_repository

    def _build_deduplication_key(
        self,
        component: IntelligenceComponent,
        gate_id: str | None,
        severity: AlertSeverity,
        time_window: str,
    ) -> str:
        """Build a deterministic deduplication key for an alert."""
        gate_part = gate_id or "system"
        return f"m94:{component.value}:{gate_part}:{severity.value}:{time_window}"

    async def maybe_create_alert(
        self,
        severity: AlertSeverity,
        component: IntelligenceComponent,
        gate_id: str | None,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> OperationalAlert | None:
        """Create an alert if no recent duplicate exists.

        Uses deduplication to avoid alert storms.
        """
        if not self._settings.quality_gates_enabled:
            return None

        time_window = datetime.now(UTC).strftime("%Y%m%d%H")
        dedup_key = self._build_deduplication_key(component, gate_id, severity, time_window)

        existing = await self._alert_repository.find_alert_by_deduplication_key(dedup_key)
        if existing is not None:
            logger.debug(
                "Alert deduplicated",
                deduplication_key=dedup_key,
                existing_alert_id=existing.alert_id,
            )
            return None

        alert = OperationalAlert(
            alert_id=(
                f"alert-{component.value}-{gate_id or 'system'}-"
                f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
            ),
            severity=severity,
            component=component,
            gate_id=gate_id,
            message=message,
            details=details or {},
            resolved=False,
            created_at=datetime.now(UTC),
            deduplication_key=dedup_key,
        )

        saved = await self._alert_repository.save_alert(alert)
        logger.info(
            "Operational alert created",
            alert_id=saved.alert_id,
            severity=severity.value,
            component=component.value,
            gate_id=gate_id,
        )
        return alert

    async def resolve_alerts_for_component(
        self,
        component: IntelligenceComponent,
        gate_id: str | None = None,
    ) -> int:
        """Resolve all unresolved alerts for a component."""
        alerts, _ = await self._alert_repository.list_alerts(
            component=component.value,
            resolved=False,
        )
        resolved_count = 0
        for alert_model in alerts:
            if gate_id is not None and alert_model.gate_id != gate_id:
                continue
            await self._alert_repository.resolve_alert(alert_model.alert_id)
            resolved_count += 1
        return resolved_count

    async def resolve_alert(self, alert_id: str) -> Any:
        """Resolve a specific alert by ID."""
        return await self._alert_repository.resolve_alert(alert_id)


__all__ = ["OperationalAlertService"]
