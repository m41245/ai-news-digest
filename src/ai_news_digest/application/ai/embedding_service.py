from __future__ import annotations

from collections.abc import Generator, Sequence
from typing import TYPE_CHECKING

from ai_news_digest.application.ai.embedding_models import (
    BatchEmbeddingResult,
)
from ai_news_digest.core.config import get_settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.domain.models.semantic_document import SemanticDocument
from ai_news_digest.domain.ports.embedding_provider import EmbeddingProvider, EmbeddingResponse

if TYPE_CHECKING:
    from ai_news_digest.application.ai.provider_health_registry import (
        ProviderHealthRegistry,
    )
    from ai_news_digest.application.ai.provider_quota_registry import (
        ProviderQuotaRegistry,
    )

logger = get_logger(__name__)


class NoEmbeddingProviderError(Exception):
    pass


class EmbeddingService:
    """Select an embedding provider and generate embeddings.

    The service is provider-independent. It selects the highest-priority
    available provider that reports the required ``embedding`` capability
    and respects the configured dimension. Provider health and quota
    eligibility are checked before selection, and failures are recorded
    in the existing M78/M79 registries when available.
    """

    def __init__(
        self,
        providers: Sequence[EmbeddingProvider],
        default_model: str | None = None,
        default_dimension: int | None = None,
        health_registry: ProviderHealthRegistry | None = None,
        quota_registry: ProviderQuotaRegistry | None = None,
    ) -> None:
        self._providers = list(providers)
        self._default_model = default_model
        self._default_dimension = default_dimension
        self._health_registry = health_registry
        self._quota_registry = quota_registry

    async def generate(
        self,
        document: SemanticDocument,
    ) -> EmbeddingResponse:
        estimated_tokens = self._estimate_tokens(document)
        primary = await self._select_provider_with_governance(estimated_tokens)
        if primary is None:
            raise NoEmbeddingProviderError("No embedding provider available.")

        last_exception: Exception | None = None
        tried = set()
        for candidate in self._iter_candidates(primary):
            if candidate.id in tried:
                continue
            tried.add(candidate.id)
            try:
                result = await candidate.embed(document)
                logger.info(
                    "embedding.generated",
                    provider=result.provider,
                    model=result.model,
                    dimension=result.dimension,
                    usage_tokens=result.usage_tokens,
                )
                await self._record_success(candidate.id)
                await self._record_usage(candidate.id, result.usage_tokens)
                return result
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "embedding.provider_failed",
                    provider=candidate.id,
                    error=str(exc),
                )
                await self._record_failure(candidate.id, exc)

        raise NoEmbeddingProviderError(
            "All embedding providers failed."
        ) from last_exception

    async def generate_batch(
        self,
        documents: Sequence[SemanticDocument],
    ) -> BatchEmbeddingResult:
        if not documents:
            return BatchEmbeddingResult(results=(), provider="", model="")
        estimated_tokens = sum(
            self._estimate_tokens(doc) for doc in documents[:50]
        )
        primary = await self._select_provider_with_governance(estimated_tokens)
        if primary is None:
            raise NoEmbeddingProviderError("No embedding provider available.")

        last_exception: Exception | None = None
        tried = set()
        for candidate in self._iter_candidates(primary):
            if candidate.id in tried:
                continue
            tried.add(candidate.id)
            try:
                results = await candidate.embed_batch(list(documents))
                total_tokens = sum(r.usage_tokens for r in results)
                logger.info(
                    "embedding.batch.generated",
                    provider=candidate.id,
                    model=candidate.model_name,
                    count=len(results),
                    total_tokens=total_tokens,
                )
                await self._record_success(candidate.id)
                await self._record_usage(candidate.id, total_tokens)
                return BatchEmbeddingResult(
                    results=tuple(results),
                    provider=candidate.id,
                    model=candidate.model_name,
                    total_tokens=total_tokens,
                )
            except Exception as exc:
                last_exception = exc
                logger.warning(
                    "embedding.provider_failed",
                    provider=candidate.id,
                    error=str(exc),
                )
                await self._record_failure(candidate.id, exc)

        raise NoEmbeddingProviderError(
            "All embedding providers failed."
        ) from last_exception

    def _iter_candidates(
        self, primary: EmbeddingProvider
    ) -> Generator[EmbeddingProvider, None, None]:
        yield primary
        for candidate in self._sorted_candidates():
            if candidate.id != primary.id:
                yield candidate

    def _sorted_candidates(self, estimated_tokens: int = 0) -> list[EmbeddingProvider]:
        candidates = [
            p for p in self._providers
            if p.enabled
        ]
        candidates.sort(key=lambda p: (p.priority(), p.id))
        return candidates

    async def _select_provider_with_governance(
        self, estimated_tokens: int = 0
    ) -> EmbeddingProvider | None:
        settings = get_settings()
        if not settings.semantic_search_enabled:
            return None
        for provider in self._sorted_candidates(estimated_tokens):
            if not await self._is_provider_healthy(provider.id):
                continue
            if not await self._check_quota(provider.id, estimated_tokens):
                continue
            return provider
        return None

    async def _is_provider_healthy(self, provider_id: str) -> bool:
        if self._health_registry is None:
            return True
        try:
            return bool(await self._health_registry.is_eligible(provider_id))
        except Exception as exc:
            logger.warning(
                "embedding.health_check_failed",
                provider=provider_id,
                error=str(exc),
            )
            return True

    async def _check_quota(self, provider_id: str, estimated_tokens: int) -> bool:
        if self._quota_registry is None:
            return True
        try:
            from ai_news_digest.application.ai.quota import QuotaWindow
            eligibility = await self._quota_registry.check_quota_eligibility(
                provider_id,
                window=QuotaWindow.DAY,
                estimated_tokens=estimated_tokens,
                estimated_cost=0.0,
            )
            if not eligibility.eligible:
                logger.warning(
                    "embedding.quota_excluded",
                    provider=provider_id,
                    reason=eligibility.reason,
                )
            return eligibility.eligible
        except Exception as exc:
            logger.warning(
                "embedding.quota_check_failed",
                provider=provider_id,
                error=str(exc),
            )
            return True

    async def _record_success(self, provider_id: str) -> None:
        if self._health_registry is None:
            return
        try:
            await self._health_registry.record_success(provider_id)
        except Exception as exc:
            logger.warning(
                "Failed to record embedding provider success",
                provider=provider_id,
                error=str(exc),
            )

    async def _record_failure(self, provider_id: str, exc: Exception) -> None:
        if self._health_registry is None:
            return
        try:
            from ai_news_digest.application.ai.provider_health import classify_failure
            category = classify_failure(exc)
            await self._health_registry.record_failure(provider_id, category)
        except Exception as exc2:
            logger.warning(
                "Failed to record embedding provider failure",
                provider=provider_id,
                error=str(exc2),
            )

    async def _record_usage(self, provider_id: str, usage_tokens: int) -> None:
        if self._quota_registry is None:
            return
        try:
            from decimal import Decimal

            from ai_news_digest.application.ai.quota import ProviderUsage
            usage = ProviderUsage(
                provider_id=provider_id,
                request_count=1,
                input_tokens=usage_tokens,
                output_tokens=0,
                total_tokens=usage_tokens,
                estimated_cost=Decimal("0"),
                cost_known=False,
                usage_known=True,
            )
            await self._quota_registry.record_usage(usage)
        except Exception as exc:
            logger.warning(
                "Failed to record embedding usage",
                provider=provider_id,
                error=str(exc),
            )

    @staticmethod
    def _estimate_tokens(document: SemanticDocument) -> int:
        text = document.to_embedding_text()
        return max(1, len(text) // 4)

    @property
    def is_available(self) -> bool:
        settings = get_settings()
        if not settings.semantic_search_enabled:
            return False
        return any(p.enabled for p in self._providers)


__all__ = ["EmbeddingService", "NoEmbeddingProviderError"]
