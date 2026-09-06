from __future__ import annotations

from ai_news_digest.application.exceptions.application_error import (
    ApplicationError,
)


class StoryClusterNotFoundError(ApplicationError):
    """
    Raised when a story cluster cannot be found.
    """
