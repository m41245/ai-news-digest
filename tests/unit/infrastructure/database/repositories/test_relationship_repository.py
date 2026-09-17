"""Tests for relationship repository bidirectional queries."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.enums.entity_type import EntityType
from ai_news_digest.domain.enums.relationship_status import RelationshipStatus
from ai_news_digest.domain.enums.relationship_type import RelationshipType
from ai_news_digest.domain.models.relationship import Relationship, ProvenanceSource
from ai_news_digest.infrastructure.database.repositories.relationship_repository import (
    SqlAlchemyRelationshipRepository,
)


def _make_relationship(
    subject_type: EntityType,
    subject_id: uuid4,
    object_type: EntityType,
    object_id: uuid4,
) -> Relationship:
    return Relationship.create(
        subject_entity_type=subject_type,
        subject_entity_id=subject_id,
        relationship_type=RelationshipType.MENTIONED_WITH,
        object_entity_type=object_type,
        object_entity_id=object_id,
        status=RelationshipStatus.VERIFIED,
        confidence=0.9,
        provenance_source=ProvenanceSource.DETERMINISTIC,
    )


def _relationship_to_model(relationship: Relationship) -> MagicMock:
    model = MagicMock()
    model.id = str(relationship.id)
    model.subject_entity_type = relationship.subject_entity_type.value
    model.subject_entity_id = str(relationship.subject_entity_id)
    model.relationship_type = relationship.relationship_type.value
    model.object_entity_type = relationship.object_entity_type.value
    model.object_entity_id = str(relationship.object_entity_id)
    model.status = relationship.status.value
    model.confidence = relationship.confidence
    model.provenance_source = relationship.provenance_source.value
    model.article_id = str(relationship.article_id) if relationship.article_id else None
    model.story_cluster_id = (
        str(relationship.story_cluster_id) if relationship.story_cluster_id else None
    )
    model.claim_id = str(relationship.claim_id) if relationship.claim_id else None
    model.evidence_id = str(relationship.evidence_id) if relationship.evidence_id else None
    model.ai_provider = relationship.ai_provider
    model.ai_model = relationship.ai_model
    model.ai_prompt_version = relationship.ai_prompt_version
    model.schema_version = relationship.schema_version
    model.processing_metadata = (
        '{"test": true}' if relationship.processing_metadata else None
    )
    model.created_at = relationship.created_at
    model.updated_at = relationship.updated_at
    model.observed_at = relationship.observed_at
    model.first_observed_at = relationship.first_observed_at
    model.last_observed_at = relationship.last_observed_at
    model.valid_from = relationship.valid_from
    model.valid_to = relationship.valid_to
    model.observation_count = relationship.observation_count
    model.source_count = relationship.source_count
    model.activity_score = relationship.activity_score
    model.activity_status = relationship.activity_status.value if relationship.activity_status else None
    return model


class TestBidirectionalRelationshipQueries:
    @pytest.fixture
    def repository(self) -> SqlAlchemyRelationshipRepository:
        session = AsyncMock(spec=AsyncSession)
        return SqlAlchemyRelationshipRepository(session)

    async def test_list_for_entity_as_subject(self, repository: SqlAlchemyRelationshipRepository) -> None:
        company_id = uuid4()
        topic_id = uuid4()
        rel = _make_relationship(EntityType.COMPANY, company_id, EntityType.TOPIC, topic_id)
        model = _relationship_to_model(rel)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [model]
        repository._session.execute.return_value = mock_result

        results = await repository.list_for_entity(
            entity_type="company",
            entity_id=company_id,
        )
        assert len(results) == 1
        assert results[0].subject_entity_id == company_id
        assert results[0].object_entity_id == topic_id

    async def test_list_for_entity_as_object(self, repository: SqlAlchemyRelationshipRepository) -> None:
        company_id = uuid4()
        topic_id = uuid4()
        rel = _make_relationship(EntityType.COMPANY, company_id, EntityType.TOPIC, topic_id)
        model = _relationship_to_model(rel)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [model]
        repository._session.execute.return_value = mock_result

        results = await repository.list_for_entity(
            entity_type="topic",
            entity_id=topic_id,
        )
        assert len(results) == 1
        assert results[0].object_entity_id == topic_id

    async def test_count_for_entity_counts_both_sides(self, repository: SqlAlchemyRelationshipRepository) -> None:
        company_id = uuid4()
        topic_id = uuid4()
        rel1 = _make_relationship(EntityType.COMPANY, company_id, EntityType.TOPIC, topic_id)
        rel2 = _make_relationship(EntityType.TOPIC, topic_id, EntityType.COMPANY, company_id)

        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 2
        repository._session.execute.return_value = mock_result

        count = await repository.count_for_entity(
            entity_type="company",
            entity_id=company_id,
        )
        assert count == 2

    async def test_list_for_entity_with_temporal_both_sides(self, repository: SqlAlchemyRelationshipRepository) -> None:
        company_id = uuid4()
        topic_id = uuid4()
        rel = _make_relationship(EntityType.COMPANY, company_id, EntityType.TOPIC, topic_id)
        model = _relationship_to_model(rel)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [model]
        repository._session.execute.return_value = mock_result

        results = await repository.list_for_entity_with_temporal(
            entity_type="topic",
            entity_id=topic_id,
        )
        assert len(results) == 1
        assert results[0].object_entity_id == topic_id


__all__ = ["TestBidirectionalRelationshipQueries"]
