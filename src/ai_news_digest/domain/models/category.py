from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class Category:
    """
    Represents a news category.
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
    ) -> Category:
        return cls(
            id=uuid4(),
            name=name,
            description=description,
            created_at=datetime.utcnow(),
        )
