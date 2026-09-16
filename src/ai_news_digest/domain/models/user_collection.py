from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class UserCollection:
    """
    Represents a user-defined collection for organizing saved stories.
    """

    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        name: str,
        description: str | None = None,
    ) -> UserCollection:
        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            user_id=user_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
        )

    def update(self, *, name: str | None = None, description: str | None = None) -> None:
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        self.updated_at = datetime.now(UTC)
