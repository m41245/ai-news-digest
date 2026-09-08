from __future__ import annotations

from enum import StrEnum


class ExtractionMethod(StrEnum):
    """
    Method used to extract article content.
    """

    RSS = "rss"

    HTML = "html"

    API = "api"

    MANUAL = "manual"
