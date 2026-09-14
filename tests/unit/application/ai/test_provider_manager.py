"""
Unit tests for ProviderManager.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_news_digest.application.ai.capability import Capability
from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponse,
    AIResponseFormat,
    AIUsage,
)
from ai_news_digest.application.ai.provider_manager import ProviderManager
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.ai.providers.base import AIProvider
from ai_news_digest.core.config import Settings
from ai_news_digest.core.exceptions import ExternalServiceError


@pytest.fixture
def provider_registry() -> ProviderRegistry:
    return ProviderRegistry()


@pytest.fixture
def capability_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register_capability(
        Capability(id="test_capability", name="Test Capability")
    )
    return registry


@pytest.fixture
def decision_engine(
    provider_registry: ProviderRegistry,
    capability_registry: CapabilityRegistry,
) -> DecisionEngine:
    return DecisionEngine(provider_registry, capability_registry)


@pytest.fixture
def provider_manager(
    provider_registry: ProviderRegistry,
    capability_registry: CapabilityRegistry,
    decision_engine: DecisionEngine,
) -> ProviderManager:
    return ProviderManager(provider_registry, capability_registry, decision_engine)


@pytest.fixture
def mock_provider() -> MagicMock:
    """Mock AI provider for testing."""
    provider = MagicMock(spec=AIProvider)
    provider.id = "test-provider"
    provider.name = "Test Provider"
    provider.enabled = True
    provider.priority = MagicMock(return_value=10)
    provider.capabilities = {"test_capability"}
    provider.provider_name = "test_provider"
    provider.model_name = "test-model"
    provider.available = AsyncMock(return_value=True)
    provider.generate = AsyncMock()
    return provider


@pytest.fixture
def mock_provider_registry(
    provider_registry: ProviderRegistry,
    capability_registry: CapabilityRegistry,
    mock_provider: MagicMock,
) -> ProviderRegistry:
    provider_registry.register(mock_provider)
    for capability in mock_provider.capabilities:
        capability_registry.register_provider(capability, mock_provider.id)
    return provider_registry


@pytest.fixture(autouse=True)
def _ai_enabled() -> None:
    with patch(
        "ai_news_digest.application.ai.provider_manager.get_settings",
        return_value=Settings(ai_enabled=True),
    ):
        yield


async def test_provider_manager_generate_success(
    provider_manager: ProviderManager,
    mock_provider: MagicMock,
    mock_provider_registry: ProviderRegistry,
) -> None:
    """Test successful AI generation."""
    mock_provider.generate.return_value = AIResponse(
        provider="test-provider",
        model="test-model",
        content="Generated text",
        usage=AIUsage(prompt_tokens=10, completion_tokens=5),
        latency_ms=100.0,
    )

    request = AIRequest(
        system_prompt="Test system",
        user_prompt="Test user",
        temperature=0.5,
        max_tokens=100,
        response_format=AIResponseFormat.TEXT,
    )

    response = await provider_manager.generate(request, capability="test_capability")

    assert response.content == "Generated text"
    assert response.model == "test-model"
    mock_provider.available.assert_called_once()
    mock_provider.generate.assert_called_once_with(request)


async def test_provider_manager_no_providers(
    provider_manager: ProviderManager,
) -> None:
    """Test generation fails when no providers are available."""
    request = AIRequest(
        system_prompt="Test system",
        user_prompt="Test user",
        temperature=0.5,
        max_tokens=100,
        response_format=AIResponseFormat.TEXT,
    )

    with pytest.raises(ExternalServiceError, match="No eligible providers available"):
        await provider_manager.generate(request, capability="test_capability")


async def test_provider_manager_all_providers_fail(
    provider_manager: ProviderManager,
    mock_provider: MagicMock,
    mock_provider_registry: ProviderRegistry,
) -> None:
    """Test generation fails when all providers raise exceptions."""
    mock_provider.generate.side_effect = Exception("Provider failed")

    request = AIRequest(
        system_prompt="Test system",
        user_prompt="Test user",
        temperature=0.5,
        max_tokens=100,
        response_format=AIResponseFormat.TEXT,
    )

    with pytest.raises(ExternalServiceError, match="Every AI provider failed"):
        await provider_manager.generate(request, capability="test_capability")


async def test_provider_manager_provider_not_available(
    provider_manager: ProviderManager,
    mock_provider: MagicMock,
    mock_provider_registry: ProviderRegistry,
) -> None:
    """Test generation fails when provider is not available."""
    mock_provider.available.return_value = False

    request = AIRequest(
        system_prompt="Test system",
        user_prompt="Test user",
        temperature=0.5,
        max_tokens=100,
        response_format=AIResponseFormat.TEXT,
    )

    with pytest.raises(ExternalServiceError, match="No eligible providers available"):
        await provider_manager.generate(request, capability="test_capability")


__all__ = [
    "test_provider_manager_all_providers_fail",
    "test_provider_manager_generate_success",
    "test_provider_manager_no_providers",
    "test_provider_manager_provider_not_available",
]
