"""
Unit tests for TemporalGraphIntelligenceService.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ai_news_digest.application.services.graph_intelligence.temporal_graph_intelligence_service import (
    EntityEvolution,
    RelationshipActivity,
    RelationshipChangeEvent,
    TemporalGraphIntelligenceService,
)
from ai_news_digest.domain.enums.entity_type import EntityType
from ai_news_digest.domain.enums.relationship_activity_status import (
    RelationshipActivityStatus,
)
from ai_news_digest.domain.enums.relationship_status import RelationshipStatus
from ai_news_digest.domain.enums.relationship_type import RelationshipType
from ai_news_digest.domain.models.relationship import Relationship, ProvenanceSource


def _make_relationship(
    subject_type: str = "story",
    subject_id: str | None = None,
    rel_type: str = "related_to",
    object_type: str = "company",
    object_id: str | None = None,
    status: str = "verified",
    confidence: float | None = 0.9,
    provenance: str = "deterministic",
    article_id: str | None = None,
    observed_at: datetime | None = None,
    first_observed_at: datetime | None = None,
    last_observed_at: datetime | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    observation_count: int = 1,
    source_count: int = 1,
    activity_score: float = 0.0,
    activity_status: str = "stable",
) -> Relationship:
    return Relationship.create(
        subject_entity_type=EntityType(subject_type),
        subject_entity_id=uuid4() if subject_id is None else uuid4(),
        relationship_type=RelationshipType(rel_type),
        object_entity_type=EntityType(object_type),
        object_entity_id=uuid4() if object_id is None else uuid4(),
        status=RelationshipStatus(status),
        confidence=confidence,
        provenance_source=ProvenanceSource(provenance),
        article_id=uuid4() if article_id is None else uuid4(),
        observed_at=observed_at,
        first_observed_at=first_observed_at,
        last_observed_at=last_observed_at,
        valid_from=valid_from,
        valid_to=valid_to,
        observation_count=observation_count,
        source_count=source_count,
        activity_score=activity_score,
        activity_status=RelationshipActivityStatus(activity_status),
    )


class TestTemporalGraphIntelligenceService:
    """Tests for TemporalGraphIntelligenceService."""

    def setup_method(self) -> None:
        self.service = TemporalGraphIntelligenceService()
        self.now = datetime.now(UTC)

    def test_compute_activity_score_retracted_is_zero(self) -> None:
        """Retracted relationships should have zero activity score."""
        rel = _make_relationship(status="retracted")
        score = self.service.compute_activity_score(rel, self.now)
        assert score == 0.0

    def test_compute_activity_score_valid_to_past_is_zero(self) -> None:
        """Relationships with valid_to in the past should have zero activity score."""
        past = datetime.now(UTC).replace(year=2020)
        rel = _make_relationship(valid_to=past)
        score = self.service.compute_activity_score(rel, self.now)
        assert score == 0.0

    def test_compute_activity_score_recent_is_high(self) -> None:
        """Recently observed relationships should have high activity score."""
        recent = datetime.now(UTC)
        rel = _make_relationship(
            observed_at=recent,
            last_observed_at=recent,
            observation_count=5,
            source_count=3,
            confidence=1.0,
        )
        score = self.service.compute_activity_score(rel, self.now)
        assert score > 0.5

    def test_compute_activity_score_old_is_low(self) -> None:
        """Old relationships should have lower activity score."""
        old = datetime.now(UTC).replace(year=2020)
        rel = _make_relationship(
            observed_at=old,
            last_observed_at=old,
            observation_count=1,
            source_count=1,
            confidence=0.5,
        )
        score = self.service.compute_activity_score(rel, self.now)
        assert score < 0.3

    def test_compute_activity_score_bounded(self) -> None:
        """Activity score must be bounded between 0 and 1."""
        rel = _make_relationship(
            observation_count=100,
            source_count=100,
            confidence=1.0,
        )
        score = self.service.compute_activity_score(rel, self.now)
        assert 0.0 <= score <= 1.0

    def test_compute_activity_status_new(self) -> None:
        """Recently first-observed relationships should be NEW."""
        recent = datetime.now(UTC)
        rel = _make_relationship(
            first_observed_at=recent,
            last_observed_at=recent,
            observation_count=1,
        )
        status = self.service.compute_activity_status(rel, self.now)
        assert status == RelationshipActivityStatus.NEW

    def test_compute_activity_status_active(self) -> None:
        """Recently observed relationships with multiple observations should be ACTIVE."""
        recent = datetime.now(UTC)
        rel = _make_relationship(
            first_observed_at=recent,
            last_observed_at=recent,
            observation_count=3,
        )
        status = self.service.compute_activity_status(rel, self.now)
        assert status == RelationshipActivityStatus.ACTIVE

    def test_compute_activity_status_stable(self) -> None:
        """Relationships observed within 7 days but not very recent should be STABLE."""
        week_ago = datetime.now(UTC).replace(day=datetime.now(UTC).day - 3)
        rel = _make_relationship(
            first_observed_at=week_ago,
            last_observed_at=week_ago,
            observation_count=3,
        )
        status = self.service.compute_activity_status(rel, self.now)
        assert status == RelationshipActivityStatus.STABLE

    def test_compute_activity_status_declining(self) -> None:
        """Relationships last observed 7-14 days ago should be DECLINING."""
        ten_days_ago = datetime.now(UTC).replace(day=datetime.now(UTC).day - 10)
        rel = _make_relationship(
            first_observed_at=ten_days_ago,
            last_observed_at=ten_days_ago,
            observation_count=2,
        )
        status = self.service.compute_activity_status(rel, self.now)
        assert status == RelationshipActivityStatus.DECLINING

    def test_compute_activity_status_stale(self) -> None:
        """Relationships last observed more than 14 days ago should be STALE."""
        twenty_days_ago = datetime.now(UTC) - timedelta(days=20)
        rel = _make_relationship(
            first_observed_at=twenty_days_ago,
            last_observed_at=twenty_days_ago,
            observation_count=1,
        )
        status = self.service.compute_activity_status(rel, self.now)
        assert status == RelationshipActivityStatus.STALE

    def test_compute_activity_status_retracted_is_stale(self) -> None:
        """Retracted relationships should have STALE status."""
        rel = _make_relationship(status="retracted")
        status = self.service.compute_activity_status(rel, self.now)
        assert status == RelationshipActivityStatus.STALE

    def test_get_entity_connections_temporal_empty(self) -> None:
        """Empty relationships should return empty connections."""
        connections = self.service.get_entity_connections_temporal(
            entity_type="story",
            entity_id=str(uuid4()),
            relationships=[],
            name_resolver=lambda e_type, e_id: f"{e_type} {e_id[:8]}",
        )
        assert connections == []

    def test_get_entity_connections_temporal_retracted_excluded(self) -> None:
        """Retracted relationships should be excluded."""
        entity_id = str(uuid4())
        rel = _make_relationship(
            subject_type="story",
            subject_id=entity_id,
            object_type="company",
            status="retracted",
        )
        rel.subject_entity_id = uuid4()
        rel.object_entity_id = uuid4()

        connections = self.service.get_entity_connections_temporal(
            entity_type="story",
            entity_id=entity_id,
            relationships=[rel],
            name_resolver=lambda e_type, e_id: f"{e_type} {e_id[:8]}",
        )
        assert connections == []

    def test_get_entity_evolution_empty(self) -> None:
        """Empty relationships should return empty evolution."""
        evolution = self.service.get_entity_evolution(
            entity_type="story",
            entity_id=str(uuid4()),
            relationships=[],
            name_resolver=lambda e_type, e_id: f"{e_type} {e_id[:8]}",
        )
        assert evolution.total_connections == 0
        assert evolution.new_connections == []
        assert evolution.recently_active == []

    def test_get_entity_evolution_with_new(self) -> None:
        """New relationships should appear in new_connections."""
        entity_id = str(uuid4())
        rel = _make_relationship(
            subject_type="story",
            subject_id=entity_id,
            object_type="company",
            first_observed_at=datetime.now(UTC),
            last_observed_at=datetime.now(UTC),
            observation_count=1,
        )
        rel.subject_entity_id = uuid4()
        rel.object_entity_id = uuid4()

        evolution = self.service.get_entity_evolution(
            entity_type="story",
            entity_id=entity_id,
            relationships=[rel],
            name_resolver=lambda e_type, e_id: f"{e_type} {e_id[:8]}",
        )
        assert evolution.total_connections == 1
        assert len(evolution.new_connections) == 1

    def test_detect_relationship_changes_empty(self) -> None:
        """Empty relationships should return empty changes."""
        changes = self.service.detect_relationship_changes(
            entity_type="story",
            entity_id=str(uuid4()),
            relationships=[],
            name_resolver=lambda e_type, e_id: f"{e_type} {e_id[:8]}",
        )
        assert changes == []

    def test_detect_relationship_changes_new(self) -> None:
        """Recently first-observed relationships should produce new_connection change."""
        entity_id = str(uuid4())
        rel = _make_relationship(
            subject_type="story",
            subject_id=entity_id,
            object_type="company",
            first_observed_at=datetime.now(UTC),
            last_observed_at=datetime.now(UTC),
            observation_count=1,
        )
        rel.subject_entity_id = uuid4()
        rel.object_entity_id = uuid4()

        changes = self.service.detect_relationship_changes(
            entity_type="story",
            entity_id=entity_id,
            relationships=[rel],
            name_resolver=lambda e_type, e_id: f"{e_type} {e_id[:8]}",
        )
        assert len(changes) == 1
        assert changes[0].change_type == "new_connection"

    def test_detect_relationship_changes_stale(self) -> None:
        """Stale relationships should produce became_stale change."""
        entity_id = str(uuid4())
        twenty_days_ago = datetime.now(UTC) - timedelta(days=20)
        rel = _make_relationship(
            subject_type="story",
            subject_id=entity_id,
            object_type="company",
            first_observed_at=twenty_days_ago,
            last_observed_at=twenty_days_ago,
            observation_count=1,
        )
        rel.subject_entity_id = uuid4()
        rel.object_entity_id = uuid4()

        changes = self.service.detect_relationship_changes(
            entity_type="story",
            entity_id=entity_id,
            relationships=[rel],
            name_resolver=lambda e_type, e_id: f"{e_type} {e_id[:8]}",
        )
        assert len(changes) == 1
        assert changes[0].change_type == "became_stale"

    def test_get_relationship_activity_empty(self) -> None:
        """Empty relationships should return empty activity list."""
        activities = self.service.get_relationship_activity([])
        assert activities == []

    def test_get_relationship_activity_bounded(self) -> None:
        """Activity list should be bounded."""
        entity_id = str(uuid4())
        rels = []
        for i in range(10):
            rel = _make_relationship(
                subject_type="story",
                subject_id=entity_id,
                object_type="company",
                last_observed_at=datetime.now(UTC),
                observation_count=i + 1,
            )
            rel.subject_entity_id = uuid4()
            rel.object_entity_id = uuid4()
            rels.append(rel)

        activities = self.service.get_relationship_activity(rels)
        assert len(activities) == 10
        assert all(0.0 <= a.activity_score <= 1.0 for a in activities)

    def test_filter_relationships_at_time(self) -> None:
        """Filter should return only relationships active at the given time."""
        entity_id = str(uuid4())
        now = datetime.now(UTC)
        past = datetime(2020, 1, 1, tzinfo=UTC)
        future = datetime(2030, 1, 1, tzinfo=UTC)

        rel = _make_relationship(
            subject_type="story",
            subject_id=entity_id,
            object_type="company",
            first_observed_at=past,
            last_observed_at=now,
        )
        rel.subject_entity_id = uuid4()
        rel.object_entity_id = uuid4()

        filtered = self.service.filter_relationships_at_time([rel], now)
        assert len(filtered) == 1

        filtered_past = self.service.filter_relationships_at_time([rel], past)
        assert len(filtered_past) == 1

        rel_with_valid_to = _make_relationship(
            subject_type="story",
            subject_id=entity_id,
            object_type="company",
            first_observed_at=past,
            last_observed_at=now,
            valid_to=datetime(2025, 1, 1, tzinfo=UTC),
        )
        rel_with_valid_to.subject_entity_id = uuid4()
        rel_with_valid_to.object_entity_id = uuid4()

        filtered_after_valid_to = self.service.filter_relationships_at_time(
            [rel_with_valid_to], future
        )
        assert len(filtered_after_valid_to) == 0

    def test_record_observation_updates_fields(self) -> None:
        """record_observation should update temporal fields."""
        rel = _make_relationship(
            observation_count=1,
            source_count=1,
        )
        rel.first_observed_at = None
        rel.last_observed_at = None
        observed = datetime.now(UTC)
        rel.record_observation(observed_at=observed, source_id=uuid4())
        assert rel.last_observed_at == observed
        assert rel.observation_count == 2
        assert rel.source_count == 2
        assert rel.first_observed_at == observed
        assert rel.updated_at >= observed


__all__ = ["TestTemporalGraphIntelligenceService"]
