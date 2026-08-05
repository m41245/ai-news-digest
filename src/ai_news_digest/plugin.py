from __future__ import annotations

from abc import ABC, abstractmethod


class Plugin(ABC):
    """Base contract for platform plugins.

    A plugin is a reusable component that can be registered in a platform-level
    registry. Concrete implementations may represent AI providers, source
    adapters, exporters, storage backends, notification channels, or future
    platform extensions. The contract intentionally remains generic and does not
    assume any domain-specific behavior.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Immutable identifier used as the registry key."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable plugin name."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version string."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable plugin description."""

    @property
    @abstractmethod
    def capabilities(self) -> set[str]:
        """Set of capability names exposed by the plugin."""

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether the plugin is currently enabled."""

    @enabled.setter
    @abstractmethod
    def enabled(self, value: bool) -> None:
        """Set the enabled state."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize plugin resources and internal state."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return whether the plugin is healthy and ready for use."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release plugin resources and stop background work."""


__all__ = ["Plugin"]
