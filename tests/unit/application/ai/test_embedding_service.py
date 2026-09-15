"""Unit tests for EmbeddingService."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_news_digest.application.ai.embedding_service import (
    EmbeddingService,
    NoEmbeddingProviderError,
)
from ai_news_digest.domain.models.semantic_document import SemanticDocument
from ai_news_digest.domain.ports.embedding_provider import EmbeddingProvider


def _make_provider(id: str, priority: int = 50, enabled: bool = True, dimension: int = 3):
    provider = MagicMock(spec=EmbeddingProvider)
    provider.id = id
    provider.priority = MagicMock(return_value=priority)
    provider.enabled = enabled
    provider.dimension = dimension
    provider.model_name = f"model-{id}"
    provider.embed = AsyncMock(
        return_value=MagicMock(
            embedding=(0.1, 0.2, 0.3),
            model=f"model-{id}",
            dimension=dimension,
            provider=id,
            usage_tokens=10,
        )
    )
    provider.embed_batch = AsyncMock(
        return_value=[
            MagicMock(
                embedding=(0.1, 0.2, 0.3),
                model=f"model-{id}",
                dimension=dimension,
                provider=id,
                usage_tokens=10,
            )
        ]
    )
    return provider


@pytest.fixture
def service() -> EmbeddingService:
    with patch(
        "ai_news_digest.application.ai.embedding_service.get_settings"
    ) as mock_settings:
        mock_settings.return_value.semantic_search_enabled = True
        return EmbeddingService(providers=[])


class TestEmbeddingService:
    @pytest.mark.asyncio
    async def test_no_providers_raises(self, service: EmbeddingService) -> None:
        doc = SemanticDocument(
            id=_make_doc_id(),
            title="Test",
        )
        with pytest.raises(NoEmbeddingProviderError):
            await service.generate(doc)

    @pytest.mark.asyncio
    async def test_no_enabled_providers_raises(self) -> None:
        with patch(
            "ai_news_digest.application.ai.embedding_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.semantic_search_enabled = True
            svc = EmbeddingService(providers=[_make_provider("p1", enabled=False)])
            doc = SemanticDocument(
                id=_make_doc_id(),
                title="Test",
            )
            with pytest.raises(NoEmbeddingProviderError):
                await svc.generate(doc)

    @pytest.mark.asyncio
    async def test_generates_embedding(self) -> None:
        with patch(
            "ai_news_digest.application.ai.embedding_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.semantic_search_enabled = True
            provider = _make_provider("p1")
            svc = EmbeddingService(providers=[provider])
            doc = SemanticDocument(
                id=_make_doc_id(),
                title="Test",
            )
            result = await svc.generate(doc)
            assert result.embedding == (0.1, 0.2, 0.3)
            provider.embed.assert_awaited_once_with(doc)

    @pytest.mark.asyncio
    async def test_selects_highest_priority(self) -> None:
        with patch(
            "ai_news_digest.application.ai.embedding_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.semantic_search_enabled = True
            low = _make_provider("low", priority=100)
            high = _make_provider("high", priority=1)
            svc = EmbeddingService(providers=[low, high])
            doc = SemanticDocument(
                id=_make_doc_id(),
                title="Test",
            )
            await svc.generate(doc)
            high.embed.assert_awaited_once()
            low.embed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_generate_batch(self) -> None:
        with patch(
            "ai_news_digest.application.ai.embedding_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.semantic_search_enabled = True
            provider = _make_provider("p1")
            svc = EmbeddingService(providers=[provider])
            docs = [
                SemanticDocument(id=_make_doc_id(), title="A"),
                SemanticDocument(id=_make_doc_id(), title="B"),
            ]
            provider.embed_batch = AsyncMock(
                return_value=[
                    MagicMock(
                        embedding=(0.1, 0.2, 0.3),
                        model="model-p1",
                        dimension=3,
                        provider="p1",
                        usage_tokens=10,
                    ),
                    MagicMock(
                        embedding=(0.1, 0.2, 0.3),
                        model="model-p1",
                        dimension=3,
                        provider="p1",
                        usage_tokens=10,
                    ),
                ]
            )
            result = await svc.generate_batch(docs)
            assert len(result.results) == 2
            provider.embed_batch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_is_available_false_when_empty(self, service: EmbeddingService) -> None:
        assert service.is_available is False

    @pytest.mark.asyncio
    async def test_is_available_true_when_enabled(self) -> None:
        with patch(
            "ai_news_digest.application.ai.embedding_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.semantic_search_enabled = True
            svc = EmbeddingService(providers=[_make_provider("p1")])
            assert svc.is_available is True

    @pytest.mark.asyncio
    async def test_fallback_on_provider_failure(self) -> None:
        with patch(
            "ai_news_digest.application.ai.embedding_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.semantic_search_enabled = True
            failing = _make_provider("failing", priority=1)
            failing.embed = AsyncMock(side_effect=RuntimeError("provider down"))
            healthy = _make_provider("healthy", priority=2)
            svc = EmbeddingService(providers=[failing, healthy])
            doc = SemanticDocument(id=_make_doc_id(), title="Test")
            result = await svc.generate(doc)
            assert result.provider == "healthy"
            healthy.embed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_unhealthy_provider(self) -> None:
        with patch(
            "ai_news_digest.application.ai.embedding_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.semantic_search_enabled = True
            unhealthy = _make_provider("unhealthy", priority=1)
            healthy = _make_provider("healthy", priority=2)
            health_registry = MagicMock()
            health_registry.is_eligible = AsyncMock(
                side_effect=lambda pid: pid == "healthy"
            )
            svc = EmbeddingService(
                providers=[unhealthy, healthy],
                health_registry=health_registry,
            )
            doc = SemanticDocument(id=_make_doc_id(), title="Test")
            result = await svc.generate(doc)
            assert result.provider == "healthy"
            unhealthy.embed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_quota_exhausted_provider(self) -> None:
        with patch(
            "ai_news_digest.application.ai.embedding_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.semantic_search_enabled = True
            exhausted = _make_provider("exhausted", priority=1)
            available = _make_provider("available", priority=2)
            quota_registry = MagicMock()
            quota_registry.check_quota_eligibility = AsyncMock(
                side_effect=lambda pid, **kwargs: MagicMock(
                    eligible=pid == "available"
                )
            )
            svc = EmbeddingService(
                providers=[exhausted, available],
                quota_registry=quota_registry,
            )
            doc = SemanticDocument(id=_make_doc_id(), title="Test")
            result = await svc.generate(doc)
            assert result.provider == "available"
            exhausted.embed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_records_success_in_health_registry(self) -> None:
        with patch(
            "ai_news_digest.application.ai.embedding_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.semantic_search_enabled = True
            provider = _make_provider("p1")
            health_registry = MagicMock()
            health_registry.is_eligible = AsyncMock(return_value=True)
            health_registry.record_success = AsyncMock()
            svc = EmbeddingService(
                providers=[provider],
                health_registry=health_registry,
            )
            doc = SemanticDocument(id=_make_doc_id(), title="Test")
            await svc.generate(doc)
            health_registry.record_success.assert_awaited_once_with("p1")

    @pytest.mark.asyncio
    async def test_records_failure_in_health_registry(self) -> None:
        with patch(
            "ai_news_digest.application.ai.embedding_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.semantic_search_enabled = True
            provider = _make_provider("p1")
            provider.embed = AsyncMock(side_effect=RuntimeError("down"))
            health_registry = MagicMock()
            health_registry.is_eligible = AsyncMock(return_value=True)
            health_registry.record_failure = AsyncMock()
            svc = EmbeddingService(
                providers=[provider],
                health_registry=health_registry,
            )
            doc = SemanticDocument(id=_make_doc_id(), title="Test")
            with pytest.raises(NoEmbeddingProviderError):
                await svc.generate(doc)
            health_registry.record_failure.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_records_usage_in_quota_registry(self) -> None:
        with patch(
            "ai_news_digest.application.ai.embedding_service.get_settings"
        ) as mock_settings:
            mock_settings.return_value.semantic_search_enabled = True
            provider = _make_provider("p1")
            quota_registry = MagicMock()
            quota_registry.check_quota_eligibility = AsyncMock(
                return_value=MagicMock(eligible=True)
            )
            quota_registry.record_usage = AsyncMock()
            svc = EmbeddingService(
                providers=[provider],
                quota_registry=quota_registry,
            )
            doc = SemanticDocument(id=_make_doc_id(), title="Test")
            await svc.generate(doc)
            quota_registry.record_usage.assert_awaited_once()


def _make_doc_id() -> str:
    import uuid

    return str(uuid.uuid4())
