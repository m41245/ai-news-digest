"""
Unit tests for ProviderRegistry.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

import pytest

from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.ai.providers.base import AIProvider
from ai_news_digest.exceptions import InvalidPluginError


@pytest.fixture
def mock_provider() -> MagicMock:
    """Mock AI provider for testing."""
    provider = MagicMock(spec=AIProvider)
    provider.id = "test-provider"
    return provider


def test_provider_registry_register(mock_provider: MagicMock) -> None:
    """Test registering a provider."""
    # Arrange
    registry = ProviderRegistry(free_only=False)

    # Act
    result = registry.register(mock_provider)

    # Assert
    assert result is mock_provider
    assert "test-provider" in registry
    assert len(registry) == 1


def test_provider_registry_register_invalid() -> None:
    """Test registering a non-provider raises error."""
    # Arrange
    registry = ProviderRegistry(free_only=False)
    invalid_provider = "not a provider"

    # Act & Assert
    with pytest.raises(InvalidPluginError, match="AIProvider"):
        registry.register(cast(AIProvider, invalid_provider))


def test_provider_registry_unregister(mock_provider: MagicMock) -> None:
    """Test unregistering a provider."""
    # Arrange
    registry = ProviderRegistry(free_only=False)
    registry.register(mock_provider)

    # Act
    result = registry.unregister("test-provider")

    # Assert
    assert result is mock_provider
    assert "test-provider" not in registry
    assert len(registry) == 0


def test_provider_registry_get(mock_provider: MagicMock) -> None:
    """Test getting a provider by ID."""
    # Arrange
    registry = ProviderRegistry(free_only=False)
    registry.register(mock_provider)

    # Act
    result = registry.get("test-provider")

    # Assert
    assert result is mock_provider


def test_provider_registry_list_all(mock_provider: MagicMock) -> None:
    """Test listing all providers."""
    # Arrange
    registry = ProviderRegistry(free_only=False)
    registry.register(mock_provider)

    # Act
    result = registry.list_all()

    # Assert
    assert len(result) == 1
    assert result[0] is mock_provider


def test_provider_registry_exists(mock_provider: MagicMock) -> None:
    """Test checking if provider exists."""
    # Arrange
    registry = ProviderRegistry(free_only=False)
    registry.register(mock_provider)

    # Act & Assert
    assert registry.exists("test-provider") is True
    assert registry.exists("non-existent") is False


def test_provider_registry_contains(mock_provider: MagicMock) -> None:
    """Test 'in' operator support."""
    # Arrange
    registry = ProviderRegistry(free_only=False)
    registry.register(mock_provider)

    # Act & Assert
    assert "test-provider" in registry
    assert "non-existent" not in registry


def test_provider_registry_len(mock_provider: MagicMock) -> None:
    """Test len() operator support."""
    # Arrange
    registry = ProviderRegistry(free_only=False)

    # Act & Assert
    assert len(registry) == 0

    registry.register(mock_provider)
    assert len(registry) == 1


@pytest.mark.parametrize(
    ("provider_id", "model_name"),
    [
        ("gemini", "gemini-2.0-flash"),
        ("groq", "llama-3.3-70b-versatile"),
    ],
)
def test_provider_registry_rejects_non_allowlisted_free_models(
    mock_provider: MagicMock,
    provider_id: str,
    model_name: str,
) -> None:
    mock_provider.id = provider_id
    mock_provider.model_name = model_name
    registry = ProviderRegistry(free_only=False)

    with pytest.raises(InvalidPluginError, match="allowlisted free-tier model"):
        registry.register(mock_provider)


@pytest.mark.parametrize(
    ("provider_id", "model_name"),
    [
        ("gemini", "gemini-3.8-flash"),
        ("groq", "openai/gpt-oss-20b"),
    ],
)
def test_provider_registry_accepts_allowlisted_free_models(
    mock_provider: MagicMock,
    provider_id: str,
    model_name: str,
) -> None:
    mock_provider.id = provider_id
    mock_provider.model_name = model_name
    registry = ProviderRegistry(free_only=False)

    assert registry.register(mock_provider) is mock_provider
    assert registry.get(provider_id) is mock_provider


def test_provider_registry_iter(mock_provider: MagicMock) -> None:
    """Test iteration over providers."""
    # Arrange
    registry = ProviderRegistry(free_only=False)
    registry.register(mock_provider)

    # Act
    providers = list(registry)

    # Assert
    assert len(providers) == 1
    assert providers[0] is mock_provider


def test_provider_registry_names(mock_provider: MagicMock) -> None:
    """Test getting provider names."""
    # Arrange
    registry = ProviderRegistry(free_only=False)
    registry.register(mock_provider)

    # Act
    names = registry.names()

    # Assert
    assert names == ["test-provider"]


def test_provider_registry_all(mock_provider: MagicMock) -> None:
    """Test all() method returns all providers."""
    # Arrange
    registry = ProviderRegistry(free_only=False)
    registry.register(mock_provider)

    # Act
    result = registry.all()

    # Assert
    assert len(result) == 1
    assert result[0] is mock_provider


def test_provider_registry_default_construction_rejects_paid_provider(
    monkeypatch: pytest.MonkeyPatch, mock_provider: MagicMock
) -> None:
    from ai_news_digest.core.config import Settings

    monkeypatch.setattr(
        "ai_news_digest.application.ai.free_models.get_settings",
        lambda: Settings(ai_free_only=True, environment="testing"),
    )
    mock_provider.id = "openai"
    mock_provider.model_name = "gpt-4o"
    registry = ProviderRegistry()
    with pytest.raises(InvalidPluginError, match="allowlisted free-tier model"):
        registry.register(mock_provider)


def test_provider_registry_default_construction_allows_test_injection_override(
    mock_provider: MagicMock,
) -> None:
    registry = ProviderRegistry(free_only=False)
    assert registry.register(mock_provider) is mock_provider
