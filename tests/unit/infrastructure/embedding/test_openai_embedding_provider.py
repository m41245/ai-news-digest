"""
Unit tests for OpenAI embedding provider.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.domain.models.semantic_document import SemanticDocument
from ai_news_digest.infrastructure.embedding.openai_embedding_provider import (
    OpenAIEmbeddingProvider,
)


def _doc() -> SemanticDocument:
    return SemanticDocument(id=uuid4(), title="Title", summary="Summary")


class TestOpenAIEmbeddingProvider:
    def test_properties(self) -> None:
        client = MagicMock()
        provider = OpenAIEmbeddingProvider(client=client, model="m", dimension=4)
        assert provider.id == "openai-embedding-m"
        assert provider.name == "OpenAI Embedding (m)"
        assert provider.model_name == "m"
        assert provider.version == "1.0.0"
        assert provider.description == "OpenAI text embedding provider."
        assert provider.enabled is True
        provider.enabled = False
        assert provider.enabled is True
        assert provider.priority() == 100
        assert provider.provider_config is None

    def test_post_init_creates_client(self) -> None:
        import os

        os.environ["OPENAI_API_KEY"] = "test-key"
        try:
            provider = OpenAIEmbeddingProvider(model="m", dimension=4)
            assert provider.client is not None
        finally:
            os.environ.pop("OPENAI_API_KEY", None)

    @pytest.mark.asyncio
    async def test_health_check_success(self) -> None:
        client = MagicMock()
        client.embeddings.create = AsyncMock(return_value=MagicMock())
        provider = OpenAIEmbeddingProvider(client=client, model="m", dimension=4)
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self) -> None:
        client = MagicMock()
        client.embeddings.create = AsyncMock(side_effect=RuntimeError("boom"))
        provider = OpenAIEmbeddingProvider(client=client, model="m", dimension=4)
        assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_do_embed(self) -> None:
        client = MagicMock()
        response = SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3, 0.4])],
            usage=SimpleNamespace(prompt_tokens=5),
        )
        client.embeddings.create = AsyncMock(return_value=response)
        provider = OpenAIEmbeddingProvider(client=client, model="m", dimension=4)
        result = await provider._do_embed(_doc())
        assert result.dimension == 4
        assert result.usage_tokens == 5

    @pytest.mark.asyncio
    async def test_do_embed_batch(self) -> None:
        client = MagicMock()
        response = SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[0.1, 0.2, 0.3, 0.4]),
                SimpleNamespace(embedding=[0.5, 0.6, 0.7, 0.8]),
            ],
            usage=SimpleNamespace(prompt_tokens=10),
        )
        client.embeddings.create = AsyncMock(return_value=response)
        provider = OpenAIEmbeddingProvider(client=client, model="m", dimension=4)
        results = await provider._do_embed_batch([_doc(), _doc()])
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_embed_dimension_mismatch(self) -> None:
        client = MagicMock()
        response = SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, 0.2])], usage=SimpleNamespace(prompt_tokens=5)
        )
        client.embeddings.create = AsyncMock(return_value=response)
        provider = OpenAIEmbeddingProvider(client=client, model="m", dimension=4)
        with pytest.raises(ValueError):
            await provider.embed(_doc())

    @pytest.mark.asyncio
    async def test_embed_batch_empty(self) -> None:
        client = MagicMock()
        provider = OpenAIEmbeddingProvider(client=client, model="m", dimension=4)
        assert await provider.embed_batch([]) == []

    def test_initialize_and_shutdown(self) -> None:
        client = MagicMock()
        provider = OpenAIEmbeddingProvider(client=client, model="m", dimension=4)
        provider.initialize()
        import asyncio

        asyncio.run(provider.shutdown())


__all__ = ["TestOpenAIEmbeddingProvider"]
