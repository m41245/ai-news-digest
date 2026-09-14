"""
Unit tests for ProviderManager health-aware routing integration.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_news_digest.application.ai.capability import Capability
from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.errors import AITimeoutError, AITransientError
from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponse,
    AIUsage,
)
from ai_news_digest.application.ai.provider_health import CircuitState, FailureCategory
from ai_news_digest.application.ai.provider_manager import ProviderManager
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.ai.providers.base import AIProvider
from ai_news_digest.application.ai.provider_health_registry import ProviderHealthRegistry
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
def health_registry() -> MagicMock:
    registry = MagicMock(spec=ProviderHealthRegistry)
    registry.is_eligible = AsyncMock(return_value=True)
    registry.record_success = AsyncMock()
    registry.record_failure = AsyncMock()
    registry.get_state = AsyncMock()
    registry.try_acquire_probe_lease = AsyncMock(return_value=False)
    return registry


@pytest.fixture
def provider_manager(
    provider_registry: ProviderRegistry,
    capability_registry: CapabilityRegistry,
    decision_engine: DecisionEngine,
    health_registry: MagicMock,
) -> ProviderManager:
    return ProviderManager(
        provider_registry,
        capability_registry,
        decision_engine,
        health_registry=health_registry,
    )


@pytest.fixture(autouse=True)
def _ai_enabled() -> None:
    with patch(
        "ai_news_digest.application.ai.provider_manager.get_settings",
        return_value=Settings(ai_enabled=True),
    ):
        yield


def _make_provider(
    provider_id: str,
    name: str,
    capabilities: set[str],
    enabled: bool = True,
    priority: int = 50,
    available: bool = True,
) -> MagicMock:
    provider = MagicMock(spec=AIProvider)
    provider.id = provider_id
    provider.name = name
    provider.enabled = enabled
    provider.priority = MagicMock(return_value=priority)
    provider.capabilities = capabilities
    provider.provider_name = name.lower().replace(" ", "_")
    provider.model_name = f"{provider_id}-model"
    provider.available = AsyncMock(return_value=available)
    provider.generate = AsyncMock()
    return provider


def _register_providers(
    provider_registry: ProviderRegistry,
    capability_registry: CapabilityRegistry,
    *providers: AIProvider,
) -> None:
    for provider in providers:
        provider_registry.register(provider)
        for capability in provider.capabilities:
            if not capability_registry.exists(capability):
                capability_registry.register_capability(
                    Capability(id=capability, name=capability.title())
                )
            capability_registry.register_provider(capability, provider.id)


class TestProviderManagerHealthRouting:
    async def test_open_provider_excluded_from_routing(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        health_registry: MagicMock,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        open_provider = _make_provider("openai", "OpenAI", {"summarization"}, priority=100)
        closed_provider = _make_provider("anthropic", "Anthropic", {"summarization"}, priority=50)
        _register_providers(provider_registry, capability_registry, open_provider, closed_provider)

        async def is_eligible(provider_id: str) -> bool:
            return provider_id != "openai"

        health_registry.is_eligible.side_effect = is_eligible

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id == "anthropic"
        assert "openai" in [pid for pid, _ in decision.rejected_provider_ids]

    async def test_preferred_open_provider_not_forced(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        health_registry: MagicMock,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        preferred = _make_provider("gemini", "Gemini", {"summarization"}, priority=100)
        fallback = _make_provider("openai", "OpenAI", {"summarization"}, priority=50)
        _register_providers(provider_registry, capability_registry, preferred, fallback)

        async def is_eligible(provider_id: str) -> bool:
            return provider_id != "gemini"

        health_registry.is_eligible.side_effect = is_eligible

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(
            request, capability="summarization", preferred_provider="gemini"
        )

        assert decision.selected_provider_id == "openai"

    async def test_health_registry_called_on_success(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        health_registry: MagicMock,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        provider = _make_provider("openai", "OpenAI", {"summarization"}, priority=100)
        _register_providers(provider_registry, capability_registry, provider)
        provider.generate.return_value = AIResponse(
            provider="openai",
            model="gpt-4",
            content="summary",
            usage=AIUsage(),
            latency_ms=100.0,
        )

        request = AIRequest(system_prompt="s", user_prompt="u")
        await provider_manager.generate(request, capability="summarization")

        health_registry.record_success.assert_called_once_with("openai")

    async def test_health_registry_called_on_failure(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
        health_registry: MagicMock,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        failing = _make_provider("openai", "OpenAI", {"summarization"}, priority=100)
        succeeding = _make_provider("anthropic", "Anthropic", {"summarization"}, priority=50)
        _register_providers(provider_registry, capability_registry, failing, succeeding)
        failing.generate.side_effect = AITimeoutError("timeout")
        succeeding.generate.return_value = AIResponse(
            provider="anthropic",
            model="claude",
            content="summary",
            usage=AIUsage(),
            latency_ms=100.0,
        )

        request = AIRequest(system_prompt="s", user_prompt="u")
        await provider_manager.generate(request, capability="summarization")

        health_registry.record_failure.assert_called_once_with("openai", FailureCategory.TIMEOUT)


__all__ = ["TestProviderManagerHealthRouting"]
