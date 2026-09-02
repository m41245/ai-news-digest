"""
Unit tests for ingestion exceptions.
"""

from __future__ import annotations

from ai_news_digest.application.services.ingestion.exceptions import (
    DuplicateArticleError,
    FeedProcessingError,
    IngestionError,
)


def test_ingestion_error_instantiation() -> None:
    """Test IngestionError can be instantiated."""
    error = IngestionError("Ingestion failed")
    assert isinstance(error, Exception)
    assert str(error) == "Ingestion failed"


def test_feed_processing_error_instantiation() -> None:
    """Test FeedProcessingError can be instantiated."""
    error = FeedProcessingError("Feed processing failed")
    assert isinstance(error, Exception)
    assert isinstance(error, IngestionError)


def test_feed_processing_error_inheritance() -> None:
    """Test FeedProcessingError inherits from IngestionError."""
    error = FeedProcessingError()
    assert isinstance(error, IngestionError)


def test_duplicate_article_error_instantiation() -> None:
    """Test DuplicateArticleError can be instantiated."""
    error = DuplicateArticleError("Duplicate article")
    assert isinstance(error, Exception)
    assert isinstance(error, IngestionError)


def test_duplicate_article_error_inheritance() -> None:
    """Test DuplicateArticleError inherits from IngestionError."""
    error = DuplicateArticleError()
    assert isinstance(error, IngestionError)


def test_all_exceptions_are_different_types() -> None:
    """Test all ingestion exceptions are distinct types."""
    ingestion = IngestionError()
    feed = FeedProcessingError()
    duplicate = DuplicateArticleError()

    assert type(ingestion) is not type(feed)
    assert type(feed) is not type(duplicate)
    assert type(ingestion) is not type(duplicate)
