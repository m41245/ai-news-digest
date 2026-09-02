"""
Unit tests for core di module.
"""

from __future__ import annotations

from ai_news_digest.core.config import Settings, get_settings


def test_get_settings() -> None:
    """Test get_settings returns Settings instance."""
    settings = get_settings()

    assert isinstance(settings, Settings)


def test_get_settings_cached() -> None:
    """Test get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2
