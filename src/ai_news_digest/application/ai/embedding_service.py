from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ai_news_digest.application.ai.embedding_models import (
    BatchEmbeddingResult,
)
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.models.semantic_document import SemanticDocument
from ai_news_digest.domain.ports.embedding_provider import EmbeddingProvider, EmbeddingResponse

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class NoEmbeddingProviderError(Exception):
    pass


class EmbeddingService:
    """Select an embedding provider and generate embeddings.

    The service is provider-independent. It selects the highest-priority
    available provider that reports the required ``embedding`` capability
    and respects the configured dimension.
    """

    def __init__(
        self,
        providers: Sequence[EmbeddingProvider],
        default_model: str | None = None,
        default_dimension: int | None = None,
    ) -> None:
        self._providers = list(providers)
        self._default_model = default_model
        self._default_dimension = default_dimension

    async def generate(
        self,
        document: SemanticDocument,
    ) -> EmbeddingResponse:
        provider = self._select_provider()
        if provider is None:
            raise NoEmbeddingProviderError("No embedding provider available.")
        try:
            result = await provider.embed(document)
            logger.info(
                "embedding.generated",
                provider=result.provider,
                model=result.model,
                dimension=result.dimension,
                usage_tokens=result.usage_tokens,
            )
            return result
        except Exception as exc:
            logger.warning(
                "embedding.provider_failed",
                provider=provider.id,
                error=str(exc),
            )
            raise

    async def generate_batch(
        self,
        documents: Sequence[SemanticDocument],
    ) -> BatchEmbeddingResult:
        provider = self._select_provider()
        if provider is None:
            raise NoEmbeddingProviderError("No embedding provider available.")
        try:
            results = await provider.embed_batch(list(documents))
            total_tokens = sum(r.usage_tokens for r in results)
            logger.info(
                "embedding.batch.generated",
                provider=provider.id,
                model=provider.model_name,
                count=len(results),
                total_tokens=total_tokens,
            )
            return BatchEmbeddingResult(
                results=tuple(results),
                provider=provider.id,
                model=provider.model_name,
                total_tokens=total_tokens,
            )
        except Exception as exc:
            logger.warning(
                "embedding.provider_failed",
                provider=provider.id,
                error=str(exc),
            )
            raise

    def _select_provider(self) -> EmbeddingProvider | None:
        settings = get_settings()
        if not settings.semantic_search_enabled:
            return None
        available = [p for p in self._providers if p.enabled]
        if not available:
            return None
        available.sort(key=lambda p: (p.priority(), p.id))
        return available[0]

    @property
    def is_available(self) -> bool:
        return self._select_provider() is not None


__all__ = ["EmbeddingService", "NoEmbeddingProviderError"]
