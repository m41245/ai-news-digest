"""
Unit tests for CapabilityRegistry.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.ai.capability import Capability
from ai_news_digest.application.ai.capability_registry import CapabilityRegistry


@pytest.fixture
def registry() -> CapabilityRegistry:
    """Create a CapabilityRegistry instance."""
    return CapabilityRegistry()


@pytest.fixture
def sample_capability() -> Capability:
    """Create a sample Capability."""
    return Capability(
        id="test_capability",
        name="Test Capability",
        description="A test capability",
        category="test",
    )


def test_capability_registry_register_capability(
    registry: CapabilityRegistry, sample_capability: Capability
) -> None:
    """Test registering a new capability."""
    result = registry.register_capability(sample_capability)

    assert result == sample_capability
    assert registry.exists("test_capability")


def test_capability_registry_register_duplicate(
    registry: CapabilityRegistry, sample_capability: Capability
) -> None:
    """Test registering duplicate capability raises ValueError."""
    registry.register_capability(sample_capability)

    with pytest.raises(ValueError, match="already registered"):
        registry.register_capability(sample_capability)


def test_capability_registry_remove_capability(
    registry: CapabilityRegistry, sample_capability: Capability
) -> None:
    """Test removing a capability."""
    registry.register_capability(sample_capability)

    result = registry.remove_capability("test_capability")

    assert result == sample_capability
    assert not registry.exists("test_capability")


def test_capability_registry_remove_capability_not_found(registry: CapabilityRegistry) -> None:
    """Test removing non-existent capability raises KeyError."""
    with pytest.raises(KeyError, match="was not found"):
        registry.remove_capability("nonexistent")


def test_capability_registry_register_provider(
    registry: CapabilityRegistry, sample_capability: Capability
) -> None:
    """Test registering a provider for a capability."""
    registry.register_capability(sample_capability)

    registry.register_provider("test_capability", "provider1")

    providers = registry.providers_for("test_capability")
    assert "provider1" in providers


def test_capability_registry_register_provider_capability_not_found(
    registry: CapabilityRegistry,
) -> None:
    """Test registering provider for non-existent capability raises KeyError."""
    with pytest.raises(KeyError, match="was not found"):
        registry.register_provider("nonexistent", "provider1")


def test_capability_registry_remove_provider(
    registry: CapabilityRegistry, sample_capability: Capability
) -> None:
    """Test removing a provider from a capability."""
    registry.register_capability(sample_capability)
    registry.register_provider("test_capability", "provider1")

    registry.remove_provider("test_capability", "provider1")

    providers = registry.providers_for("test_capability")
    assert "provider1" not in providers


def test_capability_registry_remove_provider_capability_not_found(
    registry: CapabilityRegistry,
) -> None:
    """Test removing provider from non-existent capability raises KeyError."""
    with pytest.raises(KeyError, match="was not found"):
        registry.remove_provider("nonexistent", "provider1")


def test_capability_registry_remove_provider_not_found(
    registry: CapabilityRegistry, sample_capability: Capability
) -> None:
    """Test removing non-existent provider raises KeyError."""
    registry.register_capability(sample_capability)

    with pytest.raises(KeyError, match="was not found"):
        registry.remove_provider("test_capability", "nonexistent_provider")


def test_capability_registry_remove_provider_last_provider(
    registry: CapabilityRegistry, sample_capability: Capability
) -> None:
    """Test removing last provider removes capability mapping."""
    registry.register_capability(sample_capability)
    registry.register_provider("test_capability", "provider1")

    registry.remove_provider("test_capability", "provider1")

    # Should not raise when checking providers after removal
    providers = registry.providers_for("test_capability")
    assert len(providers) == 0


def test_capability_registry_providers_for(
    registry: CapabilityRegistry, sample_capability: Capability
) -> None:
    """Test getting providers for a capability."""
    registry.register_capability(sample_capability)
    registry.register_provider("test_capability", "provider1")
    registry.register_provider("test_capability", "provider2")

    providers = registry.providers_for("test_capability")

    assert len(providers) == 2
    assert "provider1" in providers
    assert "provider2" in providers


def test_capability_registry_providers_for_not_found(registry: CapabilityRegistry) -> None:
    """Test getting providers for non-existent capability raises KeyError."""
    with pytest.raises(KeyError, match="was not found"):
        registry.providers_for("nonexistent")


def test_capability_registry_capabilities(
    registry: CapabilityRegistry, sample_capability: Capability
) -> None:
    """Test getting all capabilities."""
    registry.register_capability(sample_capability)

    capabilities = registry.capabilities()

    assert len(capabilities) == 1
    assert capabilities[0] == sample_capability


def test_capability_registry_exists(
    registry: CapabilityRegistry, sample_capability: Capability
) -> None:
    """Test exists method."""
    assert not registry.exists("test_capability")

    registry.register_capability(sample_capability)

    assert registry.exists("test_capability")


def test_capability_registry_multiple_providers_same_capability(
    registry: CapabilityRegistry, sample_capability: Capability
) -> None:
    """Test multiple providers for same capability."""
    registry.register_capability(sample_capability)
    registry.register_provider("test_capability", "provider1")
    registry.register_provider("test_capability", "provider2")
    registry.register_provider("test_capability", "provider3")

    providers = registry.providers_for("test_capability")

    assert len(providers) == 3
