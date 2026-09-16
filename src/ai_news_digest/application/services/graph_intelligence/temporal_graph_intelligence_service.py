"""
Temporal graph intelligence extension for M91.

Extends GraphIntelligenceService with temporal relationship intelligence:

- Relationship activity scoring (deterministic, bounded)
- Relationship activity status (NEW / EMERGING / ACTIVE / STABLE / DECLINING / STALE)
- Entity evolution views
- Relationship history and change detection
- Time-bounded graph traversal
- Historical connection queries
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.enums.relationship_activity_status import (
    RelationshipActivityStatus,
)
from ai_news_digest.domain.enums.relationship_status import RelationshipStatus
from ai_news_digest.domain.models.relationship import Relationship

logger = get_logger(__name__)


@dataclass(slots=True)
class RelationshipActivity:
    """Temporal activity summary for a relationship."""

    relationship_type: str
    status: str
    first_observed_at: str | None
    last_observed_at: str | None
    observation_count: int
    source_count: int
    activity_score: float
    activity_status: str
    explanation: str


@dataclass(slots=True)
class RelationshipChangeEvent:
    """A detected change in a relationship over time."""

    change_type: str
    relationship_type: str
    object_entity_type: str
    object_entity_id: str
    object_name: str
    observed_at: str | None
    explanation: str


@dataclass(slots=True)
class EntityEvolution:
    """Temporal evolution view for an entity."""

    entity_type: str
    entity_id: str
    new_connections: list[dict[str, Any]]
    recently_active: list[dict[str, Any]]
    recently_changed: list[dict[str, Any]]
    historical_connections: list[dict[str, Any]]
    total_connections: int
    generated_at: str


@dataclass(slots=True)
class TemporalGraphConnection:
    """A graph connection with temporal context."""

    entity_type: str
    entity_id: str
    name: str
    relationship_type: str | None = None
    status: str | None = None
    score: float = 0.0
    signals: list[str] = field(default_factory=list)
    explanation: str = ""
    source_count: int = 0
    is_disputed: bool = False
    is_retracted: bool = False
    first_observed_at: str | None = None
    last_observed_at: str | None = None
    observation_count: int = 0
    activity_status: str | None = None
    activity_score: float = 0.0


class TemporalGraphIntelligenceService:
    """Temporal graph intelligence extending GraphIntelligenceService.

    Computes bounded, deterministic temporal signals from relationship
    observations while reusing existing M89/M90 infrastructure.
    """

    MAX_HISTORY_ITEMS: int = 50
    MAX_EVOLUTION_ITEMS: int = 20
    RECENT_WINDOW_HOURS: float = 72.0
    ACTIVE_WINDOW_HOURS: float = 168.0
    EMERGING_WINDOW_HOURS: float = 48.0

    def compute_activity_score(
        self, relationship: Relationship, now: datetime | None = None
    ) -> float:
        """Compute a bounded deterministic activity score for a relationship.

        Score components (must sum to <= 1.0):
        - Recency: 0.0-0.4
        - Observation frequency: 0.0-0.3
        - Source diversity: 0.0-0.2
        - Confidence: 0.0-0.1
        """
        if now is None:
            now = datetime.now(UTC)

        if relationship.status == RelationshipStatus.RETRACTED:
            return 0.0

        if relationship.valid_to is not None and relationship.valid_to < now:
            return 0.0

        score = 0.0

        if relationship.last_observed_at is not None:
            age_hours = (now - relationship.last_observed_at).total_seconds() / 3600.0
            recency = max(0.0, 1.0 - (age_hours / (7 * 24)))
            score += recency * 0.4

        obs_count = relationship.observation_count or 1
        freq = min(1.0, obs_count / 10.0)
        score += freq * 0.3

        src_count = relationship.source_count or 1
        diversity = min(1.0, src_count / 5.0)
        score += diversity * 0.2

        if relationship.confidence is not None:
            score += min(1.0, max(0.0, relationship.confidence)) * 0.1

        return max(0.0, min(1.0, score))

    def compute_activity_status(
        self, relationship: Relationship, now: datetime | None = None
    ) -> RelationshipActivityStatus:
        """Compute the temporal activity status of a relationship.

        Statuses:
        - NEW: first observed recently
        - EMERGING: recent observation frequency increasing
        - ACTIVE: recently observed and supported
        - STABLE: recurring without significant recent acceleration
        - DECLINING: older observations with reduced recent activity
        - STALE: no recent supporting observation
        """
        if now is None:
            now = datetime.now(UTC)

        if relationship.status == RelationshipStatus.RETRACTED:
            return RelationshipActivityStatus.STALE

        if relationship.valid_to is not None and relationship.valid_to < now:
            return RelationshipActivityStatus.STALE

        if relationship.last_observed_at is None:
            return RelationshipActivityStatus.STABLE

        age_hours = (now - relationship.last_observed_at).total_seconds() / 3600.0

        if age_hours < self.EMERGING_WINDOW_HOURS:
            obs_count = relationship.observation_count or 1
            if obs_count >= 3:
                return RelationshipActivityStatus.ACTIVE
            if obs_count >= 2:
                return RelationshipActivityStatus.EMERGING
            return RelationshipActivityStatus.NEW

        if age_hours < self.ACTIVE_WINDOW_HOURS:
            obs_count = relationship.observation_count or 1
            if obs_count >= 3:
                return RelationshipActivityStatus.STABLE
            return RelationshipActivityStatus.ACTIVE

        if age_hours < (14 * 24):
            return RelationshipActivityStatus.DECLINING

        return RelationshipActivityStatus.STALE

    def get_entity_connections_temporal(
        self,
        entity_type: str,
        entity_id: str,
        relationships: list[Relationship],
        name_resolver: Callable[[str, str], str],
        now: datetime | None = None,
    ) -> list[TemporalGraphConnection]:
        """Return graph connections enriched with temporal metadata."""
        if now is None:
            now = datetime.now(UTC)

        connections: dict[str, TemporalGraphConnection] = {}

        for rel in relationships:
            if not self._is_active(rel.status):
                continue

            is_source = rel.subject_entity_id == entity_id
            other_type = (
                rel.object_entity_type.value
                if is_source
                else rel.subject_entity_type.value
            )
            other_id = (
                rel.object_entity_id if is_source else rel.subject_entity_id
            )

            key = f"{other_type}:{other_id}"
            if key not in connections:
                connections[key] = TemporalGraphConnection(
                    entity_type=other_type,
                    entity_id=str(other_id),
                    name=name_resolver(other_type, str(other_id)),
                )

            conn = connections[key]
            rel_score = self.compute_activity_score(rel, now)
            activity_status = self.compute_activity_status(rel, now)
            is_disputed = rel.status == RelationshipStatus.DISPUTED
            is_retracted = rel.status == RelationshipStatus.RETRACTED

            if is_retracted:
                continue

            if conn.relationship_type is None:
                conn.relationship_type = rel.relationship_type.value
                conn.status = rel.status.value
            else:
                conn.relationship_type = (
                    f"{conn.relationship_type}, {rel.relationship_type.value}"
                )

            conn.score = max(conn.score, rel_score)
            conn.is_disputed = conn.is_disputed or is_disputed
            conn.is_retracted = conn.is_retracted or is_retracted
            conn.source_count += rel.source_count or 1
            conn.observation_count += rel.observation_count or 1
            conn.activity_score = max(conn.activity_score, rel_score)
            conn.activity_status = activity_status.value

            if rel.first_observed_at and (
                conn.first_observed_at is None
                or rel.first_observed_at
                < datetime.fromisoformat(conn.first_observed_at)
            ):
                conn.first_observed_at = rel.first_observed_at.isoformat()
            if rel.last_observed_at and (
                conn.last_observed_at is None
                or rel.last_observed_at
                > datetime.fromisoformat(conn.last_observed_at)
            ):
                conn.last_observed_at = rel.last_observed_at.isoformat()

        result: list[TemporalGraphConnection] = []
        for conn in connections.values():
            if conn.is_retracted:
                continue

            explanation_parts = []
            if conn.relationship_type:
                explanation_parts.append(f"Relationship: {conn.relationship_type}")

            if conn.source_count > 1:
                explanation_parts.append(f"{conn.source_count} independent sources")

            if conn.is_disputed:
                explanation_parts.append("(disputed)")
                conn.signals.append("disputed_relationship")
            else:
                conn.signals.append("verified_relationship")

            if conn.activity_status == RelationshipActivityStatus.ACTIVE.value:
                explanation_parts.append("recently active")
                conn.signals.append("recently_active")
            elif conn.activity_status == RelationshipActivityStatus.STALE.value:
                explanation_parts.append("stale")
                conn.signals.append("stale")
            elif conn.activity_status == RelationshipActivityStatus.NEW.value:
                explanation_parts.append("new connection")
                conn.signals.append("new_connection")
            elif conn.activity_status == RelationshipActivityStatus.EMERGING.value:
                explanation_parts.append("emerging")
                conn.signals.append("emerging")
            elif conn.activity_status == RelationshipActivityStatus.DECLINING.value:
                explanation_parts.append("declining")
                conn.signals.append("declining")

            if conn.first_observed_at:
                formatted = datetime.fromisoformat(
                    conn.first_observed_at
                ).strftime("%b %Y")
                explanation_parts.append(
                    f"First observed {formatted}"
                )

            conn.explanation = "; ".join(explanation_parts) if explanation_parts else "Connected"
            result.append(conn)

        result.sort(key=lambda c: c.score, reverse=True)
        return result

    def get_entity_evolution(
        self,
        entity_type: str,
        entity_id: str,
        relationships: list[Relationship],
        name_resolver: Callable[[str, str], str],
        now: datetime | None = None,
    ) -> EntityEvolution:
        """Return a bounded entity evolution view."""
        if now is None:
            now = datetime.now(UTC)

        new_connections: list[dict[str, Any]] = []
        recently_active: list[dict[str, Any]] = []
        recently_changed: list[dict[str, Any]] = []
        historical_connections: list[dict[str, Any]] = []

        temporal_conns = self.get_entity_connections_temporal(
            entity_type=entity_type,
            entity_id=entity_id,
            relationships=relationships,
            name_resolver=name_resolver,
            now=now,
        )

        for conn in temporal_conns[: self.MAX_EVOLUTION_ITEMS]:
            conn_data = {
                "entity_type": conn.entity_type,
                "entity_id": conn.entity_id,
                "name": conn.name,
                "relationship_type": conn.relationship_type,
                "status": conn.status,
                "activity_status": conn.activity_status,
                "activity_score": round(conn.activity_score, 4),
                "first_observed_at": conn.first_observed_at,
                "last_observed_at": conn.last_observed_at,
                "observation_count": conn.observation_count,
                "source_count": conn.source_count,
                "explanation": conn.explanation,
            }

            if conn.activity_status == RelationshipActivityStatus.NEW.value:
                new_connections.append(conn_data)
            elif conn.activity_status in (
                RelationshipActivityStatus.ACTIVE.value,
                RelationshipActivityStatus.EMERGING.value,
            ):
                recently_active.append(conn_data)

            if conn.activity_status in (
                RelationshipActivityStatus.DECLINING.value,
                RelationshipActivityStatus.STALE.value,
            ):
                historical_connections.append(conn_data)

            if conn.activity_status == RelationshipActivityStatus.STABLE.value:
                recently_changed.append(conn_data)

        return EntityEvolution(
            entity_type=entity_type,
            entity_id=entity_id,
            new_connections=new_connections,
            recently_active=recently_active,
            recently_changed=recently_changed,
            historical_connections=historical_connections,
            total_connections=len(temporal_conns),
            generated_at=now.isoformat(),
        )

    def detect_relationship_changes(
        self,
        entity_type: str,
        entity_id: str,
        relationships: list[Relationship],
        name_resolver: Callable[[str, str], str],
        now: datetime | None = None,
    ) -> list[RelationshipChangeEvent]:
        """Detect bounded, deterministic relationship changes for an entity."""
        if now is None:
            now = datetime.now(UTC)

        changes: list[RelationshipChangeEvent] = []

        for rel in relationships:
            if not self._is_active(rel.status):
                continue

            is_source = rel.subject_entity_id == entity_id
            other_type = (
                rel.object_entity_type.value
                if is_source
                else rel.subject_entity_type.value
            )
            other_id = (
                rel.object_entity_id if is_source else rel.subject_entity_id
            )
            other_name = name_resolver(other_type, str(other_id))

            activity_status = self.compute_activity_status(rel, now)

            if rel.first_observed_at is not None:
                age_hours = (now - rel.first_observed_at).total_seconds() / 3600.0
                if age_hours < 24:
                        changes.append(
                            RelationshipChangeEvent(
                                change_type="new_connection",
                                relationship_type=rel.relationship_type.value,
                                object_entity_type=other_type,
                                object_entity_id=str(other_id),
                                object_name=other_name,
                                observed_at=rel.first_observed_at.isoformat(),
                                explanation=(
                                    f"New {rel.relationship_type.value}"
                                    " relationship first observed"
                                ),
                            )
                        )

            if (
                activity_status == RelationshipActivityStatus.ACTIVE
                and rel.observation_count
                and rel.observation_count > 1
            ):
                changes.append(
                    RelationshipChangeEvent(
                        change_type="recently_reobserved",
                        relationship_type=rel.relationship_type.value,
                        object_entity_type=other_type,
                        object_entity_id=str(other_id),
                        object_name=other_name,
                        observed_at=(
                            rel.last_observed_at.isoformat()
                            if rel.last_observed_at
                            else None
                        ),
                        explanation=f"Relationship re-observed {rel.observation_count} times",
                    )
                )

            if activity_status == RelationshipActivityStatus.DECLINING:
                changes.append(
                    RelationshipChangeEvent(
                        change_type="strength_decreased",
                        relationship_type=rel.relationship_type.value,
                        object_entity_type=other_type,
                        object_entity_id=str(other_id),
                        object_name=other_name,
                        observed_at=(
                            rel.last_observed_at.isoformat()
                            if rel.last_observed_at
                            else None
                        ),
                        explanation="Reduced recent observation activity",
                    )
                )

            if activity_status == RelationshipActivityStatus.STALE:
                changes.append(
                    RelationshipChangeEvent(
                        change_type="became_stale",
                        relationship_type=rel.relationship_type.value,
                        object_entity_type=other_type,
                        object_entity_id=str(other_id),
                        object_name=other_name,
                        observed_at=(
                            rel.last_observed_at.isoformat()
                            if rel.last_observed_at
                            else None
                        ),
                        explanation="No recent supporting observation",
                    )
                )

            if rel.status == RelationshipStatus.DISPUTED:
                changes.append(
                    RelationshipChangeEvent(
                        change_type="relationship_disputed",
                        relationship_type=rel.relationship_type.value,
                        object_entity_type=other_type,
                        object_entity_id=str(other_id),
                        object_name=other_name,
                        observed_at=(
                            rel.last_observed_at.isoformat()
                            if rel.last_observed_at
                            else None
                        ),
                        explanation="Relationship has conflicting evidence",
                    )
                )

        changes.sort(key=lambda c: c.observed_at or "", reverse=True)
        return changes[: self.MAX_HISTORY_ITEMS]

    def get_relationship_activity(
        self, relationships: list[Relationship], now: datetime | None = None
    ) -> list[RelationshipActivity]:
        """Return bounded activity summaries for relationships."""
        if now is None:
            now = datetime.now(UTC)

        activities: list[RelationshipActivity] = []
        for rel in relationships:
            if not self._is_active(rel.status):
                continue

            activity_status = self.compute_activity_status(rel, now)
            activity_score = self.compute_activity_score(rel, now)

            explanation_parts = []
            if activity_status == RelationshipActivityStatus.NEW:
                explanation_parts.append("First observed recently")
            elif activity_status == RelationshipActivityStatus.EMERGING:
                explanation_parts.append("Observation frequency increasing")
            elif activity_status == RelationshipActivityStatus.ACTIVE:
                explanation_parts.append("Recently observed and supported")
            elif activity_status == RelationshipActivityStatus.STABLE:
                explanation_parts.append("Recurring without significant acceleration")
            elif activity_status == RelationshipActivityStatus.DECLINING:
                explanation_parts.append("Older observations with reduced recent activity")
            elif activity_status == RelationshipActivityStatus.STALE:
                explanation_parts.append("No recent supporting observation")

            if rel.source_count and rel.source_count > 1:
                explanation_parts.append(f"{rel.source_count} independent sources")

            activities.append(
                RelationshipActivity(
                    relationship_type=rel.relationship_type.value,
                    status=rel.status.value,
                    first_observed_at=rel.first_observed_at.isoformat()
                    if rel.first_observed_at
                    else None,
                    last_observed_at=rel.last_observed_at.isoformat()
                    if rel.last_observed_at
                    else None,
                    observation_count=rel.observation_count or 1,
                    source_count=rel.source_count or 1,
                    activity_score=round(activity_score, 4),
                    activity_status=activity_status.value,
                    explanation="; ".join(explanation_parts),
                )
            )

        activities.sort(key=lambda a: a.activity_score, reverse=True)
        return activities

    def filter_relationships_at_time(
        self,
        relationships: list[Relationship],
        at_time: datetime,
    ) -> list[Relationship]:
        """Filter relationships that were active at a specific point in time."""
        result = []
        for rel in relationships:
            if not self._is_active(rel.status):
                continue

            first_at = rel.first_observed_at or rel.created_at

            if first_at <= at_time and (
                rel.valid_to is None or rel.valid_to >= at_time
            ):
                result.append(rel)

        return result

    def _is_active(self, status: RelationshipStatus) -> bool:
        return status not in (
            RelationshipStatus.RETRACTED,
            RelationshipStatus.INACTIVE,
        )


__all__ = [
    "EntityEvolution",
    "RelationshipActivity",
    "RelationshipChangeEvent",
    "TemporalGraphConnection",
    "TemporalGraphIntelligenceService",
]
