"""
Unit tests for ProviderConfig dataclass.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.ai.config import ProviderConfig


def test_provider_config_with_required_fields() -> None:
    """Test ProviderConfig creation with required fields only."""
    config = ProviderConfig(
        provider_name="test_provider",
        api_key="test_key",
    )

    assert config.provider_name == "test_provider"
    assert config.api_key == "test_key"
    assert config.enabled is True
    assert config.priority == 50
    assert config.base_url is None
    assert config.model is None
    assert config.timeout == 60.0
    assert config.max_retries == 3
    assert config.free_tier is False
    assert config.quality_score == 0.0
    assert config.speed_score == 0.0
    assert config.reliability_score == 0.0
    assert config.context_window == 0


def test_provider_config_with_all_fields() -> None:
    """Test ProviderConfig creation with all fields."""
    config = ProviderConfig(
        provider_name="test_provider",
        api_key="test_key",
        enabled=False,
        priority=100,
        base_url="https://api.example.com",
        model="gpt-4",
        timeout=120.0,
        max_retries=5,
        free_tier=True,
        quality_score=0.9,
        speed_score=0.8,
        reliability_score=0.95,
        context_window=128000,
    )

    assert config.provider_name == "test_provider"
    assert config.api_key == "test_key"
    assert config.enabled is False
    assert config.priority == 100
    assert config.base_url == "https://api.example.com"
    assert config.model == "gpt-4"
    assert config.timeout == 120.0
    assert config.max_retries == 5
    assert config.free_tier is True
    assert config.quality_score == 0.9
    assert config.speed_score == 0.8
    assert config.reliability_score == 0.95
    assert config.context_window == 128000


def test_provider_config_with_none_api_key() -> None:
    """Test ProviderConfig with None API key."""
    config = ProviderConfig(
        provider_name="test_provider",
        api_key=None,
    )

    assert config.api_key is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("enabled", False),
        ("priority", 10),
        ("timeout", 30.0),
        ("max_retries", 1),
        ("free_tier", True),
        ("quality_score", 1.0),
        ("speed_score", 1.0),
        ("reliability_score", 1.0),
        ("context_window", 32000),
    ],
)
def test_provider_config_optional_fields(field_name: str, value: object) -> None:
    """Test ProviderConfig with various optional field values."""
    config = ProviderConfig(
        provider_name="test_provider",
        api_key="test_key",
        **{field_name: value},  # type: ignore[arg-type]
    )

    assert getattr(config, field_name) == value
