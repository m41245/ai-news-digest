from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class FollowedStory:
    """
    Represents a user following a story cluster to track its evolution.
    """

    id: UUID
    user_id: UUID
    story_cluster_id: UUID
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        story_cluster_id: UUID,
    ) -> FollowedStory:
        return cls(
            id=uuid4(),
            user_id=user_id,
            story_cluster_id=story_cluster_id,
            created_at=datetime.now(UTC),
        )
