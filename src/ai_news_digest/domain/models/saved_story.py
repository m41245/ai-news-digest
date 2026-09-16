from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class SavedStory:
    """
    Represents a user saving a story cluster for later reference.
    """

    id: UUID
    user_id: UUID
    story_cluster_id: UUID
    collection_id: UUID | None = None
    note: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        story_cluster_id: UUID,
        collection_id: UUID | None = None,
        note: str | None = None,
    ) -> SavedStory:
        return cls(
            id=uuid4(),
            user_id=user_id,
            story_cluster_id=story_cluster_id,
            collection_id=collection_id,
            note=note,
            created_at=datetime.now(UTC),
        )
