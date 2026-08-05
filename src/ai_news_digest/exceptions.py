from __future__ import annotations


class PluginError(RuntimeError):
    """Base exception for all plugin-related failures."""


class InvalidPluginError(PluginError):
    """Raised when a plugin instance or plugin id is invalid."""


class DuplicatePluginError(PluginError):
    """Raised when a plugin id is registered more than once."""


class PluginNotFoundError(PluginError):
    """Raised when a plugin cannot be found in the registry."""


__all__ = [
    "PluginError",
    "InvalidPluginError",
    "DuplicatePluginError",
    "PluginNotFoundError",
]
