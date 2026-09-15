from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.domain.enums.relationship_status import RelationshipStatus
from ai_news_digest.domain.models.relationship import ProvenanceSource, Relationship
from ai_news_digest.domain.ports.relationship_repository import RelationshipRepository
from ai_news_digest.infrastructure.database.models.relationship_model import (
    RelationshipModel,
)


class SqlAlchemyRelationshipRepository(RelationshipRepository):
    """SQLAlchemy implementation of RelationshipRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, relationship_id: UUID) -> Relationship | None:
        result = await self._session.execute(
            select(RelationshipModel).where(RelationshipModel.id == str(relationship_id))
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_for_entity(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Relationship]:
        statement = select(RelationshipModel).where(
            (RelationshipModel.subject_entity_type == entity_type)
            & (RelationshipModel.subject_entity_id == str(entity_id))
        )
        if status:
            statement = statement.where(RelationshipModel.status == status)
        statement = statement.limit(limit).offset(offset).order_by(
            RelationshipModel.created_at.desc()
        )
        result = await self._session.execute(statement)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def list_related(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        relationship_types: list[str] | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Relationship]:
        statement = select(RelationshipModel).where(
            (RelationshipModel.subject_entity_type == entity_type)
            & (RelationshipModel.subject_entity_id == str(entity_id))
        )
        if relationship_types:
            statement = statement.where(
                RelationshipModel.relationship_type.in_(relationship_types)
            )
        if status:
            statement = statement.where(RelationshipModel.status == status)
        statement = statement.limit(limit).order_by(RelationshipModel.created_at.desc())
        result = await self._session.execute(statement)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def create(self, relationship: Relationship) -> Relationship:
        model = self._to_model(relationship)
        self._session.add(model)
        await self._session.flush()
        return self._to_domain(model)

    async def bulk_create(
        self, relationships: list[Relationship]
    ) -> list[Relationship]:
        models = [self._to_model(r) for r in relationships]
        self._session.add_all(models)
        await self._session.flush()
        return [self._to_domain(m) for m in models]

    async def update_status(
        self,
        relationship_id: UUID,
        status: str,
    ) -> Relationship | None:
        result = await self._session.execute(
            select(RelationshipModel).where(
                RelationshipModel.id == str(relationship_id)
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.status = RelationshipStatus(status)
        await self._session.flush()
        return self._to_domain(model)

    async def delete(self, relationship_id: UUID) -> None:
        result = await self._session.execute(
            select(RelationshipModel).where(
                RelationshipModel.id == str(relationship_id)
            )
        )
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)

    async def count_for_entity(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        status: str | None = None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(RelationshipModel)
            .where(
                (RelationshipModel.subject_entity_type == entity_type)
                & (RelationshipModel.subject_entity_id == str(entity_id))
            )
        )
        if status:
            statement = statement.where(RelationshipModel.status == status)
        result = await self._session.execute(statement)
        return result.scalar_one() or 0

    async def get_canonical(
        self,
        *,
        subject_entity_type: str,
        subject_entity_id: UUID,
        relationship_type: str,
        object_entity_type: str,
        object_entity_id: UUID,
    ) -> Relationship | None:
        result = await self._session.execute(
            select(RelationshipModel).where(
                (RelationshipModel.subject_entity_type == subject_entity_type)
                & (RelationshipModel.subject_entity_id == str(subject_entity_id))
                & (RelationshipModel.relationship_type == relationship_type)
                & (RelationshipModel.object_entity_type == object_entity_type)
                & (RelationshipModel.object_entity_id == str(object_entity_id))
            )
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    @staticmethod
    def _to_domain(model: RelationshipModel) -> Relationship:
        from ai_news_digest.domain.enums.entity_type import EntityType
        from ai_news_digest.domain.enums.relationship_status import RelationshipStatus
        from ai_news_digest.domain.enums.relationship_type import RelationshipType

        return Relationship(
            id=UUID(model.id),
            subject_entity_type=EntityType(model.subject_entity_type),
            subject_entity_id=UUID(model.subject_entity_id),
            relationship_type=RelationshipType(model.relationship_type),
            object_entity_type=EntityType(model.object_entity_type),
            object_entity_id=UUID(model.object_entity_id),
            status=RelationshipStatus(model.status),
            confidence=model.confidence,
            provenance_source=ProvenanceSource(model.provenance_source),
            article_id=UUID(model.article_id) if model.article_id else None,
            story_cluster_id=UUID(model.story_cluster_id) if model.story_cluster_id else None,
            claim_id=UUID(model.claim_id) if model.claim_id else None,
            evidence_id=UUID(model.evidence_id) if model.evidence_id else None,
            ai_provider=model.ai_provider,
            ai_model=model.ai_model,
            ai_prompt_version=model.ai_prompt_version,
            schema_version=model.schema_version,
            processing_metadata=(
                json.loads(model.processing_metadata) if model.processing_metadata else {}
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
            observed_at=model.observed_at,
        )

    @staticmethod
    def _to_model(relationship: Relationship) -> RelationshipModel:
        return RelationshipModel(
            id=str(relationship.id),
            subject_entity_type=relationship.subject_entity_type,
            subject_entity_id=str(relationship.subject_entity_id),
            relationship_type=relationship.relationship_type,
            object_entity_type=relationship.object_entity_type,
            object_entity_id=str(relationship.object_entity_id),
            status=relationship.status,
            confidence=relationship.confidence,
            provenance_source=relationship.provenance_source,
            article_id=str(relationship.article_id) if relationship.article_id else None,
            story_cluster_id=(
                str(relationship.story_cluster_id)
                if relationship.story_cluster_id
                else None
            ),
            claim_id=str(relationship.claim_id) if relationship.claim_id else None,
            evidence_id=str(relationship.evidence_id) if relationship.evidence_id else None,
            ai_provider=relationship.ai_provider,
            ai_model=relationship.ai_model,
            ai_prompt_version=relationship.ai_prompt_version,
            schema_version=relationship.schema_version,
            processing_metadata=(
                json.dumps(relationship.processing_metadata, ensure_ascii=False)
                if relationship.processing_metadata
                else None
            ),
            created_at=relationship.created_at,
            updated_at=relationship.updated_at,
            observed_at=relationship.observed_at,
        )
