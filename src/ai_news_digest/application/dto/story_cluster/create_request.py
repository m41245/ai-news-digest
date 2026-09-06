from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CreateStoryClusterRequest:
    """
    Request DTO for creating a story cluster.
    """

    title: str
    slug: str
    summary: str | None = None
