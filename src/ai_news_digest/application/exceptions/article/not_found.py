from __future__ import annotations

from ai_news_digest.application.exceptions.application_error import (
    ApplicationError,
)


class ArticleNotFoundError(ApplicationError):
    """
    Raised when an article cannot be found.
    """
