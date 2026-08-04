from __future__ import annotations

from ai_news_digest.application.exceptions.application_error import (
    ApplicationError,
)


class SourceAlreadyExistsError(ApplicationError):
    """
    Raised when attempting to create a source whose feed URL
    already exists.
    """
