from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class Topic:
    """
    Represents a topic entity referenced by articles.
    """

    id: UUID
    name: str
    created_at: datetime
    slug: str | None = None
    article_count: int = 0

    @classmethod
    def create(
        cls,
        name: str,
        slug: str | None = None,
    ) -> Topic:
        return cls(
            id=uuid4(),
            name=name,
            created_at=datetime.now(UTC),
            slug=slug,
        )


__all__ = ["Topic"]
