from __future__ import annotations

from enum import StrEnum


class ArticleStatus(StrEnum):
    """
    Processing lifecycle of an article.
    """

    NEW = "new"

    FETCHED = "fetched"

    SUMMARIZED = "summarized"

    CATEGORIZED = "categorized"

    PUBLISHED = "published"

    FAILED = "failed"
