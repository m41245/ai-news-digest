from __future__ import annotations

from collections.abc import Iterable

from ai_news_digest.exceptions import (
    DuplicatePluginError,
    InvalidPluginError,
    PluginNotFoundError,
)
from ai_news_digest.plugin import Plugin


class PluginRegistry:
    """Registry of platform plugins keyed by plugin.id.

    The registry intentionally remains generic. It only manages registration,
    lookup, enumeration, and lifecycle metadata for plugins. It does not perform
    discovery, scoring, scheduling, execution, or provider-specific behavior.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> Plugin:
        """Register a plugin using its immutable identifier."""
        self._validate_plugin(plugin)

        plugin_id = plugin.id
        if plugin_id in self._plugins:
            raise DuplicatePluginError(f"Plugin with id '{plugin_id}' is already registered.")

        self._plugins[plugin_id] = plugin
        return plugin

    def unregister(self, plugin_id: str) -> Plugin:
        """Remove and return a plugin by its unique id."""
        self._validate_plugin_id(plugin_id)

        if plugin_id not in self._plugins:
            raise PluginNotFoundError(f"Plugin with id '{plugin_id}' was not found.")

        return self._plugins.pop(plugin_id)

    def get(self, plugin_id: str) -> Plugin:
        """Return a plugin by its unique id."""
        self._validate_plugin_id(plugin_id)

        if plugin_id not in self._plugins:
            raise PluginNotFoundError(f"Plugin with id '{plugin_id}' was not found.")

        return self._plugins[plugin_id]

    def list(self) -> list[Plugin]:
        """Return all registered plugins in insertion order."""
        return list(self._plugins.values())

    def exists(self, plugin_id: str) -> bool:
        """Return True when a plugin id is already registered."""
        self._validate_plugin_id(plugin_id)
        return plugin_id in self._plugins

    @staticmethod
    def _validate_plugin(plugin: Plugin) -> None:
        """Validate a plugin instance before registration."""
        if not isinstance(plugin, Plugin):
            raise InvalidPluginError("Plugin registration requires an instance of Plugin.")

        if not plugin.id or not plugin.id.strip():
            raise InvalidPluginError("Plugin id cannot be empty.")

    @staticmethod
    def _validate_plugin_id(plugin_id: str) -> None:
        """Validate a lookup key before registry access."""
        if not isinstance(plugin_id, str):
            raise InvalidPluginError("Plugin id must be a string.")

        if not plugin_id or not plugin_id.strip():
            raise InvalidPluginError("Plugin id cannot be empty.")

    def __contains__(self, plugin_id: str) -> bool:
        """Support 'plugin_id in registry' checks."""
        return self.exists(plugin_id)

    def __len__(self) -> int:
        """Return the number of registered plugins."""
        return len(self._plugins)

    def __iter__(self) -> Iterable[Plugin]:
        """Iterate over registered plugins."""
        return iter(self._plugins.values())


__all__ = ["PluginRegistry"]
