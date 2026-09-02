"""
Unit tests for ProviderManager.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponse,
    AIResponseFormat,
    AIUsage,
)
from ai_news_digest.application.ai.provider_manager import ProviderManager
from ai_news_digest.core.exceptions import ExternalServiceError


@pytest.fixture
def mock_provider() -> MagicMock:
    """Mock AI provider for testing."""
    provider = MagicMock()
    provider.id = "test-provider"
    provider.available = AsyncMock(return_value=True)
    provider.priority = MagicMock(return_value=10)
    provider.generate = AsyncMock()
    return provider


@pytest.fixture
def mock_provider_registry(mock_provider: MagicMock) -> MagicMock:
    """Mock ProviderRegistry for testing."""
    registry = MagicMock()
    registry.__iter__ = MagicMock(return_value=iter([mock_provider]))
    return registry


async def test_provider_manager_generate_success(
    mock_provider: MagicMock,
    mock_provider_registry: MagicMock,
) -> None:
    """Test successful AI generation."""
    # Arrange
    mock_provider.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content="Generated text",
        usage=AIUsage(prompt_tokens=10, completion_tokens=5),
        latency_ms=100.0,
    )

    manager = ProviderManager(registry=mock_provider_registry)

    request = AIRequest(
        system_prompt="Test system",
        user_prompt="Test user",
        temperature=0.5,
        max_tokens=100,
        response_format=AIResponseFormat.TEXT,
    )

    # Act
    response = await manager.generate(request)

    # Assert
    assert response.content == "Generated text"
    assert response.model == "test-model"
    mock_provider.available.assert_called_once()
    mock_provider.generate.assert_called_once_with(request)


async def test_provider_manager_no_providers(mock_provider_registry: MagicMock) -> None:
    """Test generation fails when no providers are available."""
    # Arrange
    mock_provider_registry.__iter__ = MagicMock(return_value=iter([]))

    manager = ProviderManager(registry=mock_provider_registry)

    request = AIRequest(
        system_prompt="Test system",
        user_prompt="Test user",
        temperature=0.5,
        max_tokens=100,
        response_format=AIResponseFormat.TEXT,
    )

    # Act & Assert
    with pytest.raises(ExternalServiceError, match="No AI providers are currently available"):
        await manager.generate(request)


async def test_provider_manager_all_providers_fail(
    mock_provider: MagicMock,
    mock_provider_registry: MagicMock,
) -> None:
    """Test generation fails when all providers raise exceptions."""
    # Arrange
    mock_provider.generate.side_effect = Exception("Provider failed")

    manager = ProviderManager(registry=mock_provider_registry)

    request = AIRequest(
        system_prompt="Test system",
        user_prompt="Test user",
        temperature=0.5,
        max_tokens=100,
        response_format=AIResponseFormat.TEXT,
    )

    # Act & Assert
    with pytest.raises(ExternalServiceError, match="Every AI provider failed"):
        await manager.generate(request)


async def test_provider_manager_provider_not_available(
    mock_provider: MagicMock,
    mock_provider_registry: MagicMock,
) -> None:
    """Test generation skips unavailable providers."""
    # Arrange
    mock_provider.available.return_value = False

    manager = ProviderManager(registry=mock_provider_registry)

    request = AIRequest(
        system_prompt="Test system",
        user_prompt="Test user",
        temperature=0.5,
        max_tokens=100,
        response_format=AIResponseFormat.TEXT,
    )

    # Act & Assert
    with pytest.raises(ExternalServiceError, match="No AI providers are currently available"):
        await manager.generate(request)
