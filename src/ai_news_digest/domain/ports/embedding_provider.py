from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ai_news_digest.plugin import Plugin

if TYPE_CHECKING:
    from ai_news_digest.domain.models.semantic_document import SemanticDocument


@dataclass(frozen=True, slots=True)
class EmbeddingResponse:
    """Result of an embedding request."""

    embedding: tuple[float, ...]
    model: str
    dimension: int
    provider: str
    usage_tokens: int = 0


class EmbeddingProvider(Plugin, ABC):
    """Provider-independent interface for generating text embeddings.

    Embedding providers are independent from generation providers
    (AIProvider). A provider may implement both interfaces, but they
    are registered and selected independently.
    """

    @abstractmethod
    async def embed(self, document: SemanticDocument) -> EmbeddingResponse:
        """Generate an embedding for a single semantic document."""
        raise NotImplementedError

    @abstractmethod
    async def embed_batch(
        self,
        documents: list[SemanticDocument],
    ) -> list[EmbeddingResponse]:
        """Generate embeddings for multiple documents.

        Implementations may batch requests to the underlying API for
        efficiency. The returned list must be aligned with the input.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Expected embedding dimension for this provider/model."""
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Active embedding model identifier."""
        raise NotImplementedError

    @abstractmethod
    def priority(self) -> int:
        """Return provider priority for selection ordering."""
        raise NotImplementedError


__all__ = ["EmbeddingProvider", "EmbeddingResponse"]
