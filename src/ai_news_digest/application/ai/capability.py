from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Capability:
    """Metadata describing a platform capability a plugin or provider can offer.

    Capability is intentionally generic and does not include execution,
    routing, selection, or provider-specific behavior. It exists to describe the
    feature space supported by a plugin or provider without coupling the model to
    any concrete implementation.
    """

    id: str
    """Stable, unique capability identifier."""

    name: str
    """Human-readable capability name."""

    description: str = ""
    """Short description of the capability."""

    category: str = "general"
    """Capability category such as reasoning, generation, or retrieval."""

    tags: set[str] = field(default_factory=set)
    """Keyword tags used for filtering or grouping."""

    deprecated: bool = False
    """Whether the capability is deprecated."""

    experimental: bool = False
    """Whether the capability is experimental and not yet stable."""


__all__ = ["Capability"]
