"""
Unit tests for M89 knowledge graph domain models and enums.
"""

from __future__ import annotations

from ai_news_digest.domain.enums.entity_type import EntityType
from ai_news_digest.domain.enums.relationship_status import RelationshipStatus
from ai_news_digest.domain.enums.relationship_type import RelationshipType
from ai_news_digest.domain.models.relationship import (
    ProvenanceSource,
    Relationship,
)


class TestEntityType:
    def test_values(self) -> None:
        assert EntityType.COMPANY == "company"
        assert EntityType.TOPIC == "topic"
        assert EntityType.STORY == "story"
        assert EntityType.ARTICLE == "article"


class TestRelationshipType:
    def test_values(self) -> None:
        assert RelationshipType.RELATED_TO == "related_to"
        assert RelationshipType.COMPETES_WITH == "competes_with"
        assert RelationshipType.PARTNERS_WITH == "partners_with"
        assert RelationshipType.COLLABORATES_WITH == "collaborates_with"
        assert RelationshipType.USES_TECHNOLOGY == "uses_technology"
        assert RelationshipType.PROVIDES_TECHNOLOGY_TO == "provides_technology_to"
        assert RelationshipType.ANNOUNCED == "announced"
        assert RelationshipType.MENTIONED_WITH == "mentioned_with"
        assert RelationshipType.ACQUIRED == "acquired"
        assert RelationshipType.ACQUIRED_BY == "acquired_by"
        assert RelationshipType.INVESTS_IN == "invests_in"


class TestRelationshipStatus:
    def test_values(self) -> None:
        assert RelationshipStatus.CANDIDATE == "candidate"
        assert RelationshipStatus.VERIFIED == "verified"
        assert RelationshipStatus.DISPUTED == "disputed"
        assert RelationshipStatus.RETRACTED == "retracted"
        assert RelationshipStatus.INACTIVE == "inactive"


class TestRelationship:
    def test_create(self) -> None:
        rel = Relationship.create(
            subject_entity_type=EntityType.COMPANY,
            subject_entity_id="00000000-0000-0000-0000-000000000001",
            relationship_type=RelationshipType.PARTNERS_WITH,
            object_entity_type=EntityType.COMPANY,
            object_entity_id="00000000-0000-0000-0000-000000000002",
            status=RelationshipStatus.CANDIDATE,
        )
        assert rel.id is not None
        assert rel.subject_entity_type == EntityType.COMPANY
        assert rel.relationship_type == RelationshipType.PARTNERS_WITH
        assert rel.status == RelationshipStatus.CANDIDATE
        assert rel.provenance_source == ProvenanceSource.DETERMINISTIC
        assert rel.schema_version == "v1"

    def test_update_status(self) -> None:
        rel = Relationship.create(
            subject_entity_type=EntityType.COMPANY,
            subject_entity_id="00000000-0000-0000-0000-000000000001",
            relationship_type=RelationshipType.RELATED_TO,
            object_entity_type=EntityType.TOPIC,
            object_entity_id="00000000-0000-0000-0000-000000000003",
        )
        rel.update_status(RelationshipStatus.VERIFIED)
        assert rel.status == RelationshipStatus.VERIFIED

    def test_ai_extracted_provenance(self) -> None:
        rel = Relationship.create(
            subject_entity_type=EntityType.COMPANY,
            subject_entity_id="00000000-0000-0000-0000-000000000001",
            relationship_type=RelationshipType.COLLABORATES_WITH,
            object_entity_type=EntityType.COMPANY,
            object_entity_id="00000000-0000-0000-0000-000000000002",
            provenance_source=ProvenanceSource.AI_EXTRACTED,
            ai_provider="openai",
            ai_model="gpt-4",
        )
        assert rel.provenance_source == ProvenanceSource.AI_EXTRACTED
        assert rel.ai_provider == "openai"
        assert rel.ai_model == "gpt-4"


__all__ = [
    "TestEntityType",
    "TestRelationship",
    "TestRelationshipStatus",
    "TestRelationshipType",
]
