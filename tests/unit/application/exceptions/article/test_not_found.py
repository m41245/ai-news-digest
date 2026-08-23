"""
Unit tests for ArticleNotFoundError.
"""

from __future__ import annotations

from ai_news_digest.application.exceptions.article.not_found import (
    ArticleNotFoundError,
)


def test_article_not_found_error_instantiation() -> None:
    """Test ArticleNotFoundError can be instantiated."""
    error = ArticleNotFoundError()
    assert isinstance(error, Exception)


def test_article_not_found_error_message() -> None:
    """Test ArticleNotFoundError with custom message."""
    error = ArticleNotFoundError("Article not found")
    assert str(error) == "Article not found"


def test_article_not_found_error_inheritance() -> None:
    """Test ArticleNotFoundError inherits from ApplicationError."""
    from ai_news_digest.application.exceptions.application_error import (
        ApplicationError,
    )

    error = ArticleNotFoundError()
    assert isinstance(error, ApplicationError)
