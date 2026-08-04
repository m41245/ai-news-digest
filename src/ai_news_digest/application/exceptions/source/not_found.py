from __future__ import annotations

from ai_news_digest.application.exceptions.application_error import (
    ApplicationError,
)


class SourceNotFoundError(ApplicationError):
    """
    Raised when a requested news source does not exist.
    """

    def __init__(self, source_id: str) -> None:
        super().__init__(f"Source '{source_id}' was not found.")
