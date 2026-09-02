from __future__ import annotations

from enum import StrEnum


class ArticleStatus(StrEnum):
    """
    Processing lifecycle of an article.
    """

    NEW = "new"

    CATEGORIZED = "categorized"

    SUMMARIZED = "summarized"

    READY = "ready"

    FAILED = "failed"
