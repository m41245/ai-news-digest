from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SourceResponse:
    """
    Response DTO representing a news source.

    Returned by the application layer after successful operations.
    """

    id: str
    name: str
    feed_url: str
    website_url: str | None
    description: str | None
    is_active: bool
