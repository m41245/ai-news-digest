from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.models.relationship import Relationship


class RelationshipRepository:
    """Port for persisting and retrieving knowledge graph relationships."""

    async def get_by_id(self, relationship_id: UUID) -> Relationship | None:
        raise NotImplementedError

    async def list_for_entity(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Relationship]:
        raise NotImplementedError

    async def list_related(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        relationship_types: list[str] | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Relationship]:
        raise NotImplementedError

    async def create(self, relationship: Relationship) -> Relationship:
        raise NotImplementedError

    async def bulk_create(
        self, relationships: list[Relationship]
    ) -> list[Relationship]:
        raise NotImplementedError

    async def update_status(
        self,
        relationship_id: UUID,
        status: str,
    ) -> Relationship | None:
        raise NotImplementedError

    async def delete(self, relationship_id: UUID) -> None:
        raise NotImplementedError

    async def count_for_entity(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        status: str | None = None,
    ) -> int:
        raise NotImplementedError

    async def get_canonical(
        self,
        *,
        subject_entity_type: str,
        subject_entity_id: UUID,
        relationship_type: str,
        object_entity_type: str,
        object_entity_id: UUID,
    ) -> Relationship | None:
        raise NotImplementedError
