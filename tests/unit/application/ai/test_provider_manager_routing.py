"""
Unit tests for ProviderManager dynamic routing.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_news_digest.application.ai.capability import Capability
from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.errors import (
    AITimeoutError,
    AITransientError,
)
from ai_news_digest.application.ai.models import (
    AIRequest,
    AIResponse,
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
    return CapabilityRegistry()


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


class TestProviderManagerRouting:
    """Tests for ProviderManager dynamic routing."""

    async def test_route_returns_decision_with_capability(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        provider = _make_provider("openai", "OpenAI", {"summarization"}, priority=100)
        _register_providers(provider_registry, capability_registry, provider)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id == "openai"
        assert decision.capability == "summarization"
        assert decision.fallback_used is False
        assert "openai" in decision.candidate_provider_ids

    async def test_route_no_capability_uses_all_providers(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        provider = _make_provider("openai", "OpenAI", {"summarization"}, priority=100)
        _register_providers(provider_registry, capability_registry, provider)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request)

        assert decision.selected_provider_id == "openai"
        assert decision.capability is None

    async def test_route_ai_disabled_returns_no_candidates(
        self,
        provider_manager: ProviderManager,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "ai_news_digest.application.ai.provider_manager.get_settings",
            lambda: Settings(ai_enabled=False),
        )

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id is None
        assert decision.reason == "AI is disabled"

    async def test_route_preferred_provider_selected_when_eligible(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        high = _make_provider("openai", "OpenAI", {"summarization"}, priority=100)
        low = _make_provider("anthropic", "Anthropic", {"summarization"}, priority=50)
        _register_providers(provider_registry, capability_registry, high, low)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(
            request, capability="summarization", preferred_provider="anthropic"
        )

        assert decision.selected_provider_id == "anthropic"
        assert decision.attempted_provider_ids[0] == "anthropic"

    async def test_route_preferred_provider_falls_back_when_unavailable(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        preferred = _make_provider(
            "anthropic", "Anthropic", {"summarization"}, priority=50, available=False
        )
        fallback = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, available=True
        )
        _register_providers(provider_registry, capability_registry, preferred, fallback)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(
            request, capability="summarization", preferred_provider="anthropic"
        )

        assert decision.selected_provider_id == "openai"
        assert "anthropic" in [pid for pid, _ in decision.rejected_provider_ids]

    async def test_route_excluded_provider_never_selected(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        excluded = _make_provider("openai", "OpenAI", {"summarization"}, priority=100)
        allowed = _make_provider("anthropic", "Anthropic", {"summarization"}, priority=50)
        _register_providers(provider_registry, capability_registry, excluded, allowed)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(
            request, capability="summarization", excluded_providers=["openai"]
        )

        assert decision.selected_provider_id == "anthropic"
        assert "openai" in [pid for pid, _ in decision.rejected_provider_ids]

    async def test_route_disabled_provider_excluded(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        disabled = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, enabled=False
        )
        enabled = _make_provider(
            "anthropic", "Anthropic", {"summarization"}, priority=50, enabled=True
        )
        _register_providers(provider_registry, capability_registry, disabled, enabled)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id == "anthropic"
        assert "openai" in [pid for pid, _ in decision.rejected_provider_ids]

    async def test_route_incapable_provider_excluded(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        incapable = _make_provider(
            "openai", "OpenAI", {"analysis"}, priority=100
        )
        capable = _make_provider(
            "anthropic", "Anthropic", {"summarization"}, priority=50
        )
        _register_providers(provider_registry, capability_registry, incapable, capable)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id == "anthropic"
        assert "openai" not in decision.attempted_provider_ids

    async def test_route_priority_ordering(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        low = _make_provider("openai", "OpenAI", {"summarization"}, priority=10)
        high = _make_provider("anthropic", "Anthropic", {"summarization"}, priority=90)
        medium = _make_provider("gemini", "Gemini", {"summarization"}, priority=50)
        _register_providers(provider_registry, capability_registry, low, high, medium)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id == "anthropic"
        assert decision.attempted_provider_ids == ["anthropic", "gemini", "openai"]

    async def test_route_deterministic_tie_break_by_provider_id(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        p1 = _make_provider("anthropic", "Anthropic", {"summarization"}, priority=50)
        p2 = _make_provider("openai", "OpenAI", {"summarization"}, priority=50)
        _register_providers(provider_registry, capability_registry, p1, p2)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id == "anthropic"
        assert decision.attempted_provider_ids == ["anthropic", "openai"]

    async def test_route_no_eligible_providers(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        unavailable = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, available=False
        )
        _register_providers(provider_registry, capability_registry, unavailable)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id is None
        assert "openai" in [pid for pid, _ in decision.rejected_provider_ids]

    async def test_route_no_capability_candidates(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        provider = _make_provider("openai", "OpenAI", {"analysis"}, priority=100)
        _register_providers(provider_registry, capability_registry, provider)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id is None
        assert "No eligible providers" in decision.reason

    async def test_generate_uses_routing_and_returns_response(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
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
            usage=AIUsage(prompt_tokens=10, completion_tokens=5),
            latency_ms=100.0,
        )

        request = AIRequest(system_prompt="s", user_prompt="u")
        response = await provider_manager.generate(request, capability="summarization")

        assert response.content == "summary"
        assert response.provider == "openai"

    async def test_generate_raises_when_no_eligible_providers(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        unavailable = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, available=False
        )
        _register_providers(provider_registry, capability_registry, unavailable)

        request = AIRequest(system_prompt="s", user_prompt="u")
        with pytest.raises(ExternalServiceError, match="No eligible providers available"):
            await provider_manager.generate(request, capability="summarization")

    async def test_generate_falls_back_on_failure(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        failing = _make_provider("openai", "OpenAI", {"summarization"}, priority=100)
        succeeding = _make_provider(
            "anthropic", "Anthropic", {"summarization"}, priority=50
        )
        _register_providers(provider_registry, capability_registry, failing, succeeding)
        failing.generate.side_effect = AITransientError("transient failure")
        succeeding.generate.return_value = AIResponse(
            provider="anthropic",
            model="claude",
            content="summary",
            usage=AIUsage(),
            latency_ms=100.0,
        )

        request = AIRequest(system_prompt="s", user_prompt="u")
        response = await provider_manager.generate(request, capability="summarization")

        assert response.provider == "anthropic"
        assert response.content == "summary"

    async def test_generate_raises_after_all_providers_fail(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        p1 = _make_provider("openai", "OpenAI", {"summarization"}, priority=100)
        p2 = _make_provider("anthropic", "Anthropic", {"summarization"}, priority=50)
        _register_providers(provider_registry, capability_registry, p1, p2)
        p1.generate.side_effect = AITransientError("failure 1")
        p2.generate.side_effect = AITimeoutError("failure 2")

        request = AIRequest(system_prompt="s", user_prompt="u")
        with pytest.raises(ExternalServiceError, match="Every AI provider failed"):
            await provider_manager.generate(request, capability="summarization")

    async def test_generate_provider_attempted_at_most_once(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        failing = _make_provider("openai", "OpenAI", {"summarization"}, priority=100)
        succeeding = _make_provider(
            "anthropic", "Anthropic", {"summarization"}, priority=50
        )
        _register_providers(provider_registry, capability_registry, failing, succeeding)
        failing.generate.side_effect = AITransientError("failure")
        succeeding.generate.return_value = AIResponse(
            provider="anthropic",
            model="claude",
            content="summary",
            usage=AIUsage(),
            latency_ms=100.0,
        )

        request = AIRequest(system_prompt="s", user_prompt="u")
        await provider_manager.generate(request, capability="summarization")

        assert failing.generate.call_count == 1
        assert succeeding.generate.call_count == 1

    async def test_route_preferred_invalid_capability_ignored(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        provider = _make_provider("openai", "OpenAI", {"summarization"}, priority=100)
        _register_providers(provider_registry, capability_registry, provider)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(
            request, capability="summarization", preferred_provider="nonexistent"
        )

        assert decision.selected_provider_id == "openai"

    async def test_route_rate_limit_reason_in_decision(
        self,
        provider_manager: ProviderManager,
        provider_registry: ProviderRegistry,
        capability_registry: CapabilityRegistry,
    ) -> None:
        capability_registry.register_capability(
            Capability(id="summarization", name="Summarization")
        )
        rate_limited = _make_provider(
            "openai", "OpenAI", {"summarization"}, priority=100, available=False
        )
        fallback = _make_provider(
            "anthropic", "Anthropic", {"summarization"}, priority=50, available=True
        )
        _register_providers(provider_registry, capability_registry, rate_limited, fallback)

        request = AIRequest(system_prompt="s", user_prompt="u")
        decision = await provider_manager.route(request, capability="summarization")

        assert decision.selected_provider_id == "anthropic"
        assert "openai" in [pid for pid, _ in decision.rejected_provider_ids]


__all__ = ["TestProviderManagerRouting"]
