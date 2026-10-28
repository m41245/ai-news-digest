from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True, frozen=True)
class UpdateSourceRequest:
    """
    Request DTO for updating an existing news source.

    Only explicitly provided fields are updated.
    """

    id: UUID
    name: str | None = None
    feed_url: str | None = None
    website_url: str | None = None
    description: str | None = None
    is_active: bool | None = None
