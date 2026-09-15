from __future__ import annotations

from dataclasses import dataclass

from ai_news_digest.domain.ports.embedding_provider import EmbeddingResponse


@dataclass(frozen=True, slots=True)
class BatchEmbeddingResult:
    """Aggregated result of a batch embedding operation."""

    results: tuple[EmbeddingResponse, ...]
    provider: str
    model: str
    total_tokens: int = 0


__all__ = ["BatchEmbeddingResult"]
