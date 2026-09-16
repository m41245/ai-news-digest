from __future__ import annotations

from datetime import datetime
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

    async def update_observation(
        self,
        relationship_id: UUID,
        *,
        observed_at: datetime,
        source_id: UUID | None = None,
    ) -> Relationship | None:
        """Record a new observation for an existing relationship."""
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

    async def list_for_entity_with_temporal(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        status: str | None = None,
        observed_from: datetime | None = None,
        observed_to: datetime | None = None,
        active_at: datetime | None = None,
        changed_since: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Relationship]:
        """List relationships with temporal filters."""
        raise NotImplementedError

    async def list_recent(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Relationship]:
        """List recent relationships ordered by creation date."""
        raise NotImplementedError

    async def get_entity_relationship_history(
        self,
        *,
        entity_type: str,
        entity_id: UUID,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        """Return bounded relationship history for an entity."""
        raise NotImplementedError
