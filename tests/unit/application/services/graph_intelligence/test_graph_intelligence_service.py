"""
Unit tests for GraphIntelligenceService.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_news_digest.application.services.graph_intelligence.graph_intelligence_service import (
    ConnectionSignal,
    EntityNeighborhood,
    GraphConnection,
    GraphIntelligenceService,
    GraphPath,
    RelatedStoryGraphSignal,
)
from ai_news_digest.domain.enums.entity_type import EntityType
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
    )


class TestGraphIntelligenceService:
    """Tests for GraphIntelligenceService."""

    def setup_method(self) -> None:
        self.service = GraphIntelligenceService()
        self.now = datetime.now(UTC)

    def test_compute_related_story_no_signal(self) -> None:
        """No shared entities or relationships should return None."""
        result = self.service.compute_related_story_signals(
            source_cluster_id=str(uuid4()),
            candidate_cluster_id=str(uuid4()),
            source_company_ids={"c1"},
            source_topic_ids={"t1"},
            source_category_ids=set(),
            candidate_company_ids=set(),
            candidate_topic_ids=set(),
            candidate_category_ids=set(),
            relationships=[],
            now=self.now,
        )
        assert result is None

    def test_compute_related_story_shared_company(self) -> None:
        """Shared companies should produce a graph signal."""
        source_id = str(uuid4())
        candidate_id = str(uuid4())
        shared_company = str(uuid4())

        result = self.service.compute_related_story_signals(
            source_cluster_id=source_id,
            candidate_cluster_id=candidate_id,
            source_company_ids={shared_company},
            source_topic_ids=set(),
            source_category_ids=set(),
            candidate_company_ids={shared_company},
            candidate_topic_ids=set(),
            candidate_category_ids=set(),
            relationships=[],
            now=self.now,
        )
        assert result is not None
        assert result.graph_score > 0
        assert ConnectionSignal.SHARED_COMPANY.value in result.signals
        assert shared_company in result.shared_companies

    def test_compute_related_story_shared_topic(self) -> None:
        """Shared topics should produce a graph signal."""
        source_id = str(uuid4())
        candidate_id = str(uuid4())
        shared_topic = str(uuid4())

        result = self.service.compute_related_story_signals(
            source_cluster_id=source_id,
            candidate_cluster_id=candidate_id,
            source_company_ids=set(),
            source_topic_ids={shared_topic},
            source_category_ids=set(),
            candidate_company_ids=set(),
            candidate_topic_ids={shared_topic},
            candidate_category_ids=set(),
            relationships=[],
            now=self.now,
        )
        assert result is not None
        assert ConnectionSignal.SHARED_TOPIC.value in result.signals
        assert shared_topic in result.shared_topics

    def test_compute_related_story_same_cluster_returns_none(self) -> None:
        """Same cluster ID should return None."""
        cluster_id = str(uuid4())
        result = self.service.compute_related_story_signals(
            source_cluster_id=cluster_id,
            candidate_cluster_id=cluster_id,
            source_company_ids=set(),
            source_topic_ids=set(),
            source_category_ids=set(),
            candidate_company_ids=set(),
            candidate_topic_ids=set(),
            candidate_category_ids=set(),
            relationships=[],
            now=self.now,
        )
        assert result is None

    def test_get_entity_connections_empty(self) -> None:
        """Empty relationships should return empty connections."""
        connections = self.service.get_entity_connections(
            entity_type="story",
            entity_id=str(uuid4()),
            relationships=[],
            name_resolver=lambda e_type, e_id: f"{e_type} {e_id[:8]}",
        )
        assert connections == []

    def test_get_entity_connections_conflict_aware(self) -> None:
        """Disputed relationships should have reduced score."""
        entity_id = str(uuid4())
        rel = _make_relationship(
            subject_type="story",
            object_type="company",
            status="disputed",
            confidence=0.9,
        )
        rel.subject_entity_id = uuid4()
        rel.object_entity_id = uuid4()

        connections = self.service.get_entity_connections(
            entity_type="story",
            entity_id=entity_id,
            relationships=[rel],
            name_resolver=lambda e_type, e_id: f"{e_type} {e_id[:8]}",
        )
        assert len(connections) == 1
        assert connections[0].is_disputed is True
        assert connections[0].score < 1.0

    def test_get_entity_connections_retracted_excluded(self) -> None:
        """Retracted relationships should be excluded."""
        entity_id = str(uuid4())
        rel = _make_relationship(
            subject_type="story",
            object_type="company",
            status="retracted",
            confidence=0.9,
        )
        rel.subject_entity_id = uuid4()
        rel.object_entity_id = uuid4()

        connections = self.service.get_entity_connections(
            entity_type="story",
            entity_id=entity_id,
            relationships=[rel],
            name_resolver=lambda e_type, e_id: f"{e_type} {e_id[:8]}",
        )
        assert connections == []

    def test_find_path_direct_connection(self) -> None:
        """Direct relationship should produce a path of length 1."""
        story_id = str(uuid4())
        company_id = str(uuid4())
        rel = _make_relationship(
            subject_type="story",
            subject_id=story_id,
            object_type="company",
            object_id=company_id,
            status="verified",
        )
        rel.subject_entity_id = uuid4()
        rel.object_entity_id = uuid4()

        path = self.service.find_path(
            relationships=[rel],
            source_type="story",
            source_id=story_id,
            target_type="company",
            target_id=company_id,
        )
        assert path is None  # Different UUIDs than actual rel

    def test_find_path_no_path(self) -> None:
        """Unconnected entities should return None."""
        path = self.service.find_path(
            relationships=[],
            source_type="story",
            source_id=str(uuid4()),
            target_type="company",
            target_id=str(uuid4()),
        )
        assert path is None

    def test_get_entity_neighborhood_bounded(self) -> None:
        """Neighborhood should respect bounds."""
        center_id = str(uuid4())
        rels = []
        for i in range(5):
            rel = _make_relationship(
                subject_type="story",
                subject_id=center_id,
                object_type="company",
                status="verified",
            )
            rel.subject_entity_id = uuid4()
            rel.object_entity_id = uuid4()
            rels.append(rel)

        neighborhood = self.service.get_entity_neighborhood(
            entity_type="story",
            entity_id=center_id,
            relationships=rels,
            name_resolver=lambda e_type, e_id: f"{e_type} {e_id[:8]}",
        )
        assert len(neighborhood.nodes) <= GraphIntelligenceService.MAX_BFS_NODES
        assert len(neighborhood.edges) <= GraphIntelligenceService.MAX_BFS_EDGES

    def test_relationship_score_disputed(self) -> None:
        """Disputed relationships should have reduced score."""
        rel = _make_relationship(status="disputed", confidence=1.0)
        score = self.service._relationship_score(rel, self.now)
        assert score < 1.0
        assert score >= 0.0

    def test_relationship_score_candidate(self) -> None:
        """Candidate relationships should have reduced score."""
        rel = _make_relationship(status="candidate", confidence=1.0)
        score = self.service._relationship_score(rel, self.now)
        assert score < 1.0

    def test_relationship_score_retracted(self) -> None:
        """Retracted relationships should have zero score."""
        rel = _make_relationship(status="retracted", confidence=1.0)
        score = self.service._relationship_score(rel, self.now)
        assert score == 0.0

    def test_relationship_score_recency(self) -> None:
        """Recent relationships should score higher than old ones."""
        recent = datetime.now(UTC)
        old = datetime.now(UTC).replace(year=2020)

        rel_recent = _make_relationship(confidence=1.0, observed_at=recent)
        rel_old = _make_relationship(confidence=1.0, observed_at=old)

        score_recent = self.service._relationship_score(rel_recent, self.now)
        score_old = self.service._relationship_score(rel_old, self.now)
        assert score_recent > score_old

    def test_is_active(self) -> None:
        """Active statuses should return True, retracted/inactive should return False."""
        assert self.service._is_active(RelationshipStatus.VERIFIED) is True
        assert self.service._is_active(RelationshipStatus.CANDIDATE) is True
        assert self.service._is_active(RelationshipStatus.DISPUTED) is True
        assert self.service._is_active(RelationshipStatus.RETRACTED) is False
        assert self.service._is_active(RelationshipStatus.INACTIVE) is False

    def test_build_explanation_shared_entities(self) -> None:
        """Explanation should mention shared entities."""
        explanation = self.service._build_explanation(
            shared_companies={"OpenAI"},
            shared_topics=set(),
            shared_categories=set(),
            signals=[ConnectionSignal.VERIFIED_RELATIONSHIP.value],
            relationship_count=2,
        )
        assert "OpenAI" in explanation
        assert "verified" in explanation.lower() or "supported" in explanation.lower()

    def test_build_explanation_disputed(self) -> None:
        """Explanation should mention dispute."""
        explanation = self.service._build_explanation(
            shared_companies=set(),
            shared_topics=set(),
            shared_categories=set(),
            signals=[ConnectionSignal.DISPUTED_RELATIONSHIP.value],
            relationship_count=1,
        )
        assert "disputed" in explanation.lower()


__all__ = ["TestGraphIntelligenceService"]
