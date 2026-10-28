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
    status: str
    decision: str | None = None
    previous_status: str | None = None
    previous_is_active: bool | None = None
    reason: str | None = None
    validation_outcome: str | None = None
    changed: bool = False
