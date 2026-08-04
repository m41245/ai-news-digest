from __future__ import annotations

from ai_news_digest.application.exceptions.application_error import (
    ApplicationError,
)


class ArticleAlreadyExistsError(ApplicationError):
    """
    Raised when attempting to create an article that already exists.
    """
