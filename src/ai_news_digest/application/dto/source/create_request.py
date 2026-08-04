from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CreateSourceRequest:
    """
    Request DTO for creating a news source.

    This object represents the data required by the application layer
    to create a new source. It is intentionally independent of the
    domain entity and persistence models.
    """

    name: str
    feed_url: str
    website_url: str | None = None
    description: str | None = None
    is_active: bool = True
