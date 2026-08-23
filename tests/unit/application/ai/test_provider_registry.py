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
    registry = ProviderRegistry()

    # Act
    result = registry.register(mock_provider)

    # Assert
    assert result is mock_provider
    assert "test-provider" in registry
    assert len(registry) == 1


def test_provider_registry_register_invalid() -> None:
    """Test registering a non-provider raises error."""
    # Arrange
    registry = ProviderRegistry()
    invalid_provider = "not a provider"

    # Act & Assert
    with pytest.raises(InvalidPluginError, match="AIProvider"):
        registry.register(cast(AIProvider, invalid_provider))


def test_provider_registry_unregister(mock_provider: MagicMock) -> None:
    """Test unregistering a provider."""
    # Arrange
    registry = ProviderRegistry()
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
    registry = ProviderRegistry()
    registry.register(mock_provider)

    # Act
    result = registry.get("test-provider")

    # Assert
    assert result is mock_provider


def test_provider_registry_list_all(mock_provider: MagicMock) -> None:
    """Test listing all providers."""
    # Arrange
    registry = ProviderRegistry()
    registry.register(mock_provider)

    # Act
    result = registry.list_all()

    # Assert
    assert len(result) == 1
    assert result[0] is mock_provider


def test_provider_registry_exists(mock_provider: MagicMock) -> None:
    """Test checking if provider exists."""
    # Arrange
    registry = ProviderRegistry()
    registry.register(mock_provider)

    # Act & Assert
    assert registry.exists("test-provider") is True
    assert registry.exists("non-existent") is False


def test_provider_registry_contains(mock_provider: MagicMock) -> None:
    """Test 'in' operator support."""
    # Arrange
    registry = ProviderRegistry()
    registry.register(mock_provider)

    # Act & Assert
    assert "test-provider" in registry
    assert "non-existent" not in registry


def test_provider_registry_len(mock_provider: MagicMock) -> None:
    """Test len() operator support."""
    # Arrange
    registry = ProviderRegistry()

    # Act & Assert
    assert len(registry) == 0

    registry.register(mock_provider)
    assert len(registry) == 1


def test_provider_registry_iter(mock_provider: MagicMock) -> None:
    """Test iteration over providers."""
    # Arrange
    registry = ProviderRegistry()
    registry.register(mock_provider)

    # Act
    providers = list(registry)

    # Assert
    assert len(providers) == 1
    assert providers[0] is mock_provider


def test_provider_registry_names(mock_provider: MagicMock) -> None:
    """Test getting provider names."""
    # Arrange
    registry = ProviderRegistry()
    registry.register(mock_provider)

    # Act
    names = registry.names()

    # Assert
    assert names == ["test-provider"]


def test_provider_registry_all(mock_provider: MagicMock) -> None:
    """Test all() method returns all providers."""
    # Arrange
    registry = ProviderRegistry()
    registry.register(mock_provider)

    # Act
    result = registry.all()

    # Assert
    assert len(result) == 1
    assert result[0] is mock_provider
