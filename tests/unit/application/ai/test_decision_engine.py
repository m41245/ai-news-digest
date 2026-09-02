"""
Unit tests for DecisionEngine.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ai_news_digest.application.ai.capability import Capability
from ai_news_digest.application.ai.capability_registry import CapabilityRegistry
from ai_news_digest.application.ai.decision_engine import DecisionEngine
from ai_news_digest.application.ai.provider_registry import ProviderRegistry
from ai_news_digest.application.ai.providers.base import AIProvider


@pytest.fixture
def provider_registry() -> ProviderRegistry:
    """Create a ProviderRegistry instance."""
    return ProviderRegistry()


@pytest.fixture
def capability_registry() -> CapabilityRegistry:
    """Create a CapabilityRegistry instance."""
    return CapabilityRegistry()


@pytest.fixture
def decision_engine(
    provider_registry: ProviderRegistry, capability_registry: CapabilityRegistry
) -> DecisionEngine:
    """Create a DecisionEngine instance."""
    return DecisionEngine(provider_registry, capability_registry)


@pytest.fixture
def sample_capability() -> Capability:
    """Create a sample Capability."""
    return Capability(
        id="test_capability",
        name="Test Capability",
        description="A test capability",
        category="test",
    )


def test_decision_engine_resolve_empty_capabilities(decision_engine: DecisionEngine) -> None:
    """Test resolve with empty required capabilities."""
    result = decision_engine.resolve(set())

    assert result == set()


def test_decision_engine_resolve_single_capability(
    decision_engine: DecisionEngine,
    capability_registry: CapabilityRegistry,
    sample_capability: Capability,
) -> None:
    """Test resolve with single capability."""
    capability_registry.register_capability(sample_capability)
    capability_registry.register_provider("test_capability", "provider1")

    result = decision_engine.resolve({"test_capability"})

    # Provider not registered in provider_registry, so result is empty
    assert result == set()


def test_decision_engine_resolve_capability_not_exists(decision_engine: DecisionEngine) -> None:
    """Test resolve with non-existent capability."""
    result = decision_engine.resolve({"nonexistent"})

    assert result == set()


def test_decision_engine_resolve_multiple_capabilities(
    decision_engine: DecisionEngine,
    capability_registry: CapabilityRegistry,
    sample_capability: Capability,
) -> None:
    """Test resolve with multiple capabilities."""
    capability_registry.register_capability(sample_capability)
    capability2 = Capability(
        id="test_capability2",
        name="Test Capability 2",
        description="Another test capability",
        category="test",
    )
    capability_registry.register_capability(capability2)

    capability_registry.register_provider("test_capability", "provider1")
    capability_registry.register_provider("test_capability2", "provider1")

    result = decision_engine.resolve({"test_capability", "test_capability2"})

    assert result == set()  # Provider not registered in provider_registry


def test_decision_engine_resolve_no_matching_providers(
    decision_engine: DecisionEngine,
    capability_registry: CapabilityRegistry,
    sample_capability: Capability,
) -> None:
    """Test resolve when no providers match all capabilities."""
    capability_registry.register_capability(sample_capability)
    capability2 = Capability(
        id="test_capability2",
        name="Test Capability 2",
        description="Another test capability",
        category="test",
    )
    capability_registry.register_capability(capability2)

    capability_registry.register_provider("test_capability", "provider1")
    capability_registry.register_provider("test_capability2", "provider2")

    result = decision_engine.resolve({"test_capability", "test_capability2"})

    assert result == set()


def test_decision_engine_resolve_filters_nonexistent_providers(
    decision_engine: DecisionEngine,
    capability_registry: CapabilityRegistry,
    sample_capability: Capability,
) -> None:
    """Test resolve filters out providers not in provider_registry."""
    capability_registry.register_capability(sample_capability)
    capability_registry.register_provider("test_capability", "nonexistent_provider")

    result = decision_engine.resolve({"test_capability"})

    assert result == set()


def test_decision_engine_resolve_with_registered_provider(
    decision_engine: DecisionEngine,
    provider_registry: ProviderRegistry,
    capability_registry: CapabilityRegistry,
    sample_capability: Capability,
) -> None:
    """Test resolve with provider registered in both registries."""
    capability_registry.register_capability(sample_capability)
    capability_registry.register_provider("test_capability", "provider1")

    mock_provider = MagicMock(spec=AIProvider)
    mock_provider.id = "provider1"
    provider_registry.register(mock_provider)

    result = decision_engine.resolve({"test_capability"})

    assert result == {"provider1"}
