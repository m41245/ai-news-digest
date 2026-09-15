from __future__ import annotations

from enum import StrEnum


class StoryActivityStatus(StrEnum):
    """
    Activity state for a story cluster based on recent evidence.
    """

    BREAKING = "breaking"
    DEVELOPING = "developing"
    ONGOING = "ongoing"
    STALE = "stale"


__all__ = ["StoryActivityStatus"]
