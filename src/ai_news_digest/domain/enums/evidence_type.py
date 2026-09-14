from __future__ import annotations

from enum import StrEnum


class EvidenceType(StrEnum):
    """Type of evidence supporting a claim."""

    ARTICLE_TEXT = "article_text"
    ARTICLE_TITLE = "article_title"
    ARTICLE_METADATA = "article_metadata"
    RSS_CONTENT = "rss_content"
