from __future__ import annotations

from enum import StrEnum


class ExtractionQuality(StrEnum):
    """
    Quality level of extracted article content.
    """

    NONE = "none"

    LOW = "low"

    MEDIUM = "medium"

    HIGH = "high"

    FULL = "full"
