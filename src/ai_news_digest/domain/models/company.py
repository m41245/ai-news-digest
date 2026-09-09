from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class Company:
    """
    Represents a company entity referenced by articles.
    """

    id: UUID
    name: str
    description: str | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        name: str,
        description: str | None = None,
    ) -> Company:
        return cls(
            id=uuid4(),
            name=name,
            description=description,
            created_at=datetime.now(UTC),
        )


__all__ = ["Company"]
