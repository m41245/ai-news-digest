"""
Unit tests for ArticleAlreadyExistsError.
"""

from __future__ import annotations

from ai_news_digest.application.exceptions.article.already_exists import (
    ArticleAlreadyExistsError,
)


def test_article_already_exists_error_instantiation() -> None:
    """Test ArticleAlreadyExistsError can be instantiated."""
    error = ArticleAlreadyExistsError()
    assert isinstance(error, Exception)


def test_article_already_exists_error_message() -> None:
    """Test ArticleAlreadyExistsError with custom message."""
    error = ArticleAlreadyExistsError("Article already exists")
    assert str(error) == "Article already exists"


def test_article_already_exists_error_inheritance() -> None:
    """Test ArticleAlreadyExistsError inherits from ApplicationError."""
    from ai_news_digest.application.exceptions.application_error import (
        ApplicationError,
    )

    error = ArticleAlreadyExistsError()
    assert isinstance(error, ApplicationError)
