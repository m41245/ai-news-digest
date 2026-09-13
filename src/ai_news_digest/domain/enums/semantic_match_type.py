from __future__ import annotations

from enum import StrEnum


class SemanticMatchType(StrEnum):
    """
    Classification of how a new article relates to an existing story cluster
    or candidate article.

    The ordering is intentional: more specific / stronger matches come first.
    """

    EXACT_DUPLICATE = "exact_duplicate"
    SEMANTIC_DUPLICATE = "semantic_duplicate"
    RELATED_BUT_DISTINCT = "related_but_distinct"
    NEW_STORY = "new_story"


__all__ = ["SemanticMatchType"]
