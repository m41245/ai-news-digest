from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_news_digest.application.ai.embedding_provider import BaseEmbeddingProvider
from ai_news_digest.domain.models.semantic_document import SemanticDocument
from ai_news_digest.domain.ports.embedding_provider import EmbeddingResponse

try:
    from openai import AsyncOpenAI

    _openai_available = True
except ImportError:
    _openai_available = False


if _openai_available:

    @dataclass(slots=True)
    class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
        """Embedding provider for OpenAI embedding models."""

        client: Any = None
        model: str = "text-embedding-3-small"
        dimension: int = 1536
        provider_name: str = "openai"
        _config: Any = None

        def __post_init__(self) -> None:
            if self.client is None:
                self.client = AsyncOpenAI()

        @property
        def id(self) -> str:
            return f"openai-embedding-{self.model}"

        @property
        def name(self) -> str:
            return f"OpenAI Embedding ({self.model})"

        @property
        def model_name(self) -> str:
            return self.model

        @property
        def version(self) -> str:
            return "1.0.0"

        @property
        def description(self) -> str:
            return "OpenAI text embedding provider."

        @property
        def enabled(self) -> bool:
            return True

        @enabled.setter
        def enabled(self, value: bool) -> None:
            pass

        def priority(self) -> int:
            return 100

        async def health_check(self) -> bool:
            try:
                await self.client.embeddings.create(
                    model=self.model,
                    input="health check",
                    dimensions=self.dimension,
                )
                return True
            except Exception:
                return False

        def initialize(self) -> None:
            pass

        async def shutdown(self) -> None:
            pass

        async def _do_embed(
            self,
            document: SemanticDocument,
        ) -> EmbeddingResponse:
            text = document.to_embedding_text()
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimension,
            )
            data = response.data[0]
            return EmbeddingResponse(
                embedding=tuple(data.embedding),
                model=self.model,
                dimension=len(data.embedding),
                provider=self.provider_name,
                usage_tokens=response.usage.prompt_tokens,
            )

        async def _do_embed_batch(
            self,
            documents: list[SemanticDocument],
        ) -> list[EmbeddingResponse]:
            texts = [d.to_embedding_text() for d in documents]
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.dimension,
            )
            results: list[EmbeddingResponse] = []
            for _document, data in zip(documents, response.data, strict=True):
                results.append(
                    EmbeddingResponse(
                        embedding=tuple(data.embedding),
                        model=self.model,
                        dimension=len(data.embedding),
                        provider=self.provider_name,
                        usage_tokens=response.usage.prompt_tokens,
                    )
                )
            return results

else:

    @dataclass(slots=True)
    class OpenAIEmbeddingProvider:  # type: ignore[no-redef]
        """Stub when openai package is unavailable."""

        client: Any = None
        model: str = "text-embedding-3-small"
        dimension: int = 1536
        provider_name: str = "openai"
        _config: Any = None

        def __post_init__(self) -> None:
            raise ImportError(
                "openai package is required for OpenAIEmbeddingProvider."
            )


__all__ = ["OpenAIEmbeddingProvider"]
