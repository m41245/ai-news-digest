"""
Unit tests for PluginRegistry.
"""

from __future__ import annotations

import pytest

from ai_news_digest.exceptions import (
    DuplicatePluginError,
    InvalidPluginError,
    PluginNotFoundError,
)
from ai_news_digest.plugin import Plugin
from ai_news_digest.plugin_registry import PluginRegistry


class ConcretePlugin(Plugin):
    """Concrete Plugin implementation for testing."""

    def __init__(self, plugin_id: str, name: str, version: str) -> None:
        self._id = plugin_id
        self._name = name
        self._version = version

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def description(self) -> str:
        return "Test plugin"

    @property
    def capabilities(self) -> set[str]:
        return set()

    @property
    def enabled(self) -> bool:
        return True

    @enabled.setter
    def enabled(self, value: bool) -> None:
        pass

    def initialize(self) -> None:
        pass

    async def health_check(self) -> bool:
        return True

    async def shutdown(self) -> None:
        pass


@pytest.fixture
def registry() -> PluginRegistry:
    """Create a PluginRegistry instance."""
    return PluginRegistry()


@pytest.fixture
def sample_plugin() -> Plugin:
    """Create a sample Plugin."""
    return ConcretePlugin(plugin_id="test_plugin", name="Test Plugin", version="1.0.0")


def test_plugin_registry_register(registry: PluginRegistry, sample_plugin: Plugin) -> None:
    """Test registering a plugin."""
    result = registry.register(sample_plugin)

    assert result == sample_plugin
    assert registry.exists("test_plugin")


def test_plugin_registry_register_duplicate(
    registry: PluginRegistry, sample_plugin: Plugin
) -> None:
    """Test registering duplicate plugin raises DuplicatePluginError."""
    registry.register(sample_plugin)

    with pytest.raises(DuplicatePluginError, match="already registered"):
        registry.register(sample_plugin)


def test_plugin_registry_unregister(registry: PluginRegistry, sample_plugin: Plugin) -> None:
    """Test unregistering a plugin."""
    registry.register(sample_plugin)

    result = registry.unregister("test_plugin")

    assert result == sample_plugin
    assert not registry.exists("test_plugin")


def test_plugin_registry_unregister_not_found(registry: PluginRegistry) -> None:
    """Test unregistering non-existent plugin raises PluginNotFoundError."""
    with pytest.raises(PluginNotFoundError, match="was not found"):
        registry.unregister("nonexistent")


def test_plugin_registry_get(registry: PluginRegistry, sample_plugin: Plugin) -> None:
    """Test getting a plugin."""
    registry.register(sample_plugin)

    result = registry.get("test_plugin")

    assert result == sample_plugin


def test_plugin_registry_get_not_found(registry: PluginRegistry) -> None:
    """Test getting non-existent plugin raises PluginNotFoundError."""
    with pytest.raises(PluginNotFoundError, match="was not found"):
        registry.get("nonexistent")


def test_plugin_registry_list(registry: PluginRegistry, sample_plugin: Plugin) -> None:
    """Test listing all plugins."""
    registry.register(sample_plugin)

    plugins = registry.list()

    assert len(plugins) == 1
    assert plugins[0] == sample_plugin


def test_plugin_registry_list_empty(registry: PluginRegistry) -> None:
    """Test listing plugins when registry is empty."""
    plugins = registry.list()

    assert len(plugins) == 0


def test_plugin_registry_exists(registry: PluginRegistry, sample_plugin: Plugin) -> None:
    """Test exists method."""
    assert not registry.exists("test_plugin")

    registry.register(sample_plugin)

    assert registry.exists("test_plugin")


def test_plugin_registry_validate_plugin_invalid_type(registry: PluginRegistry) -> None:
    """Test validation rejects non-Plugin instances."""
    with pytest.raises(InvalidPluginError, match="requires an instance of Plugin"):
        registry.register("not a plugin")  # type: ignore


def test_plugin_registry_validate_plugin_empty_id(registry: PluginRegistry) -> None:
    """Test validation rejects empty plugin id."""
    plugin = ConcretePlugin(plugin_id="", name="Test", version="1.0.0")

    with pytest.raises(InvalidPluginError, match="cannot be empty"):
        registry.register(plugin)


def test_plugin_registry_validate_plugin_whitespace_id(registry: PluginRegistry) -> None:
    """Test validation rejects whitespace-only plugin id."""
    plugin = ConcretePlugin(plugin_id="   ", name="Test", version="1.0.0")

    with pytest.raises(InvalidPluginError, match="cannot be empty"):
        registry.register(plugin)


def test_plugin_registry_validate_plugin_id_invalid_type(registry: PluginRegistry) -> None:
    """Test validation rejects non-string plugin id."""
    with pytest.raises(InvalidPluginError, match="must be a string"):
        registry.exists(123)  # type: ignore


def test_plugin_registry_validate_plugin_id_empty(registry: PluginRegistry) -> None:
    """Test validation rejects empty plugin id string."""
    with pytest.raises(InvalidPluginError, match="cannot be empty"):
        registry.exists("")


def test_plugin_registry_validate_plugin_id_whitespace(registry: PluginRegistry) -> None:
    """Test validation rejects whitespace-only plugin id string."""
    with pytest.raises(InvalidPluginError, match="cannot be empty"):
        registry.exists("   ")


def test_plugin_registry_contains(registry: PluginRegistry, sample_plugin: Plugin) -> None:
    """Test __contains__ method."""
    assert "test_plugin" not in registry

    registry.register(sample_plugin)

    assert "test_plugin" in registry


def test_plugin_registry_len(registry: PluginRegistry, sample_plugin: Plugin) -> None:
    """Test __len__ method."""
    assert len(registry) == 0

    registry.register(sample_plugin)

    assert len(registry) == 1


def test_plugin_registry_iter(registry: PluginRegistry, sample_plugin: Plugin) -> None:
    """Test __iter__ method."""
    registry.register(sample_plugin)

    plugins = list(registry)

    assert len(plugins) == 1
    assert plugins[0] == sample_plugin


def test_plugin_registry_multiple_plugins(registry: PluginRegistry) -> None:
    """Test registry with multiple plugins."""
    plugin1 = ConcretePlugin(plugin_id="plugin1", name="Plugin 1", version="1.0.0")
    plugin2 = ConcretePlugin(plugin_id="plugin2", name="Plugin 2", version="1.0.0")
    plugin3 = ConcretePlugin(plugin_id="plugin3", name="Plugin 3", version="1.0.0")

    registry.register(plugin1)
    registry.register(plugin2)
    registry.register(plugin3)

    assert len(registry) == 3
    assert registry.exists("plugin1")
    assert registry.exists("plugin2")
    assert registry.exists("plugin3")
