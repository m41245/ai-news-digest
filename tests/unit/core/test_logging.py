"""
Unit tests for core logging module.
"""

from __future__ import annotations

from ai_news_digest.core.logging import configure_logging, get_logger


def test_configure_logging() -> None:
    """Test that configure_logging runs without errors."""
    configure_logging()

    # Should not raise any exceptions


def test_get_logger() -> None:
    """Test getting a logger."""
    configure_logging()

    logger = get_logger("test_logger")

    assert logger is not None
    assert logger.name == "test_logger"


def test_get_logger_different_names() -> None:
    """Test getting loggers with different names."""
    configure_logging()

    logger1 = get_logger("logger1")
    logger2 = get_logger("logger2")

    assert logger1.name == "logger1"
    assert logger2.name == "logger2"
