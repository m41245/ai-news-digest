from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ai_news_digest.domain.models.semantic_document import SemanticDocument
from ai_news_digest.domain.ports.embedding_provider import (
    EmbeddingProvider,
    EmbeddingResponse,
)


class BaseEmbeddingProvider(EmbeddingProvider, ABC):
    """Abstract base for embedding providers.

    Subclasses implement ``_do_embed`` and ``_do_embed_batch`` with the
    provider-specific HTTP logic. The base class handles common concerns
    such as dimension validation and error translation.
    """

    @abstractmethod
    async def _do_embed(
        self,
        document: SemanticDocument,
    ) -> EmbeddingResponse:
        raise NotImplementedError

    @abstractmethod
    async def _do_embed_batch(
        self,
        documents: list[SemanticDocument],
    ) -> list[EmbeddingResponse]:
        raise NotImplementedError

    async def embed(self, document: SemanticDocument) -> EmbeddingResponse:
        result = await self._do_embed(document)
        if result.dimension != self.dimension:
            raise ValueError(
                f"Provider returned embedding with unexpected dimension "
                f"{result.dimension}, expected {self.dimension}."
            )
        return result

    async def embed_batch(
        self,
        documents: list[SemanticDocument],
    ) -> list[EmbeddingResponse]:
        if not documents:
            return []
        results = await self._do_embed_batch(documents)
        if len(results) != len(documents):
            raise ValueError(
                f"Batch embedding returned {len(results)} results for "
                f"{len(documents)} documents."
            )
        for result in results:
            if result.dimension != self.dimension:
                raise ValueError(
                    f"Provider returned embedding with unexpected dimension "
                    f"{result.dimension}, expected {self.dimension}."
                )
        return results

    @property
    def capabilities(self) -> set[str]:
        return {"embedding"}

    @property
    def model_name(self) -> str:
        return getattr(self, "model", "")

    @abstractmethod
    def priority(self) -> int:
        """Return provider priority for selection ordering."""
        raise NotImplementedError

    @property
    def provider_config(self) -> Any:
        return getattr(self, "_config", None)


__all__ = ["BaseEmbeddingProvider"]
