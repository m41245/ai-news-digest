from __future__ import annotations


class IngestionError(Exception):
    """
    Base exception for article ingestion.
    """


class FeedProcessingError(IngestionError):
    """
    Raised when a feed cannot be processed.
    """


class DuplicateArticleError(IngestionError):
    """
    Raised when attempting to persist a duplicate article.
    """
