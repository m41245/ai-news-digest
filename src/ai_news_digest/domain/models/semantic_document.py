from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from uuid import UUID


@dataclass(frozen=True, slots=True)
class SemanticDocument:
    """Bounded semantic representation of an article or story cluster.

    Only concise, product-relevant text is included. Full article bodies,
    HTML, and tracking content are intentionally excluded.
    """

    id: UUID
    title: str
    summary: str | None = None
    why_it_matters: str | None = None
    topics: tuple[str, ...] = ()
    companies: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()

    def to_embedding_text(self) -> str:
        """Compose the text sent to an embedding provider."""
        parts: list[str] = [self.title]
        if self.summary:
            parts.append(self.summary)
        if self.why_it_matters:
            parts.append(self.why_it_matters)
        if self.topics:
            parts.append("Topics: " + ", ".join(self.topics))
        if self.companies:
            parts.append("Companies: " + ", ".join(self.companies))
        if self.categories:
            parts.append("Categories: " + ", ".join(self.categories))
        return "\n".join(parts)


__all__ = ["SemanticDocument"]
