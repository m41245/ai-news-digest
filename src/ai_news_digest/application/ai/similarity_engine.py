from __future__ import annotations

import math
from dataclasses import dataclass

from ai_news_digest.core.exceptions import AppError as ApplicationError


class SimilarityError(ApplicationError):
    """Raised when similarity computation cannot proceed."""


@dataclass(slots=True)
class SimilarityResult:
    """Cosine similarity between two vectors."""

    score: float
    is_valid: bool
    error: str | None = None


class SimilarityEngine:
    """Deterministic cosine similarity computation for embedding vectors.

    The engine validates inputs and clamps results to [0, 1] for normalized
    vectors. It never returns NaN or Infinity.
    """

    @staticmethod
    def cosine_similarity(
        a: tuple[float, ...],
        b: tuple[float, ...],
    ) -> SimilarityResult:
        if len(a) != len(b):
            return SimilarityResult(
                score=0.0,
                is_valid=False,
                error=f"Dimension mismatch: {len(a)} != {len(b)}",
            )

        if not a:
            return SimilarityResult(
                score=0.0,
                is_valid=False,
                error="Empty vectors",
            )

        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for x, y in zip(a, b, strict=True):
            dot += x * y
            norm_a += x * x
            norm_b += y * y

        if norm_a == 0.0 or norm_b == 0.0:
            return SimilarityResult(
                score=0.0,
                is_valid=True,
                error="Zero magnitude vector",
            )

        denom = math.sqrt(norm_a) * math.sqrt(norm_b)
        if denom == 0.0:
            return SimilarityResult(
                score=0.0,
                is_valid=True,
                error="Zero denominator",
            )

        score = dot / denom

        if math.isnan(score) or math.isinf(score):
            return SimilarityResult(
                score=0.0,
                is_valid=False,
                error=f"Invalid similarity value: {score}",
            )

        score = max(-1.0, min(1.0, score))
        return SimilarityResult(score=score, is_valid=True)

    @staticmethod
    def normalized_similarity(
        a: tuple[float, ...],
        b: tuple[float, ...],
    ) -> float:
        """Return a similarity in [0, 1] for normalized vectors."""
        result = SimilarityEngine.cosine_similarity(a, b)
        if not result.is_valid:
            return 0.0
        return max(0.0, result.score)


__all__ = ["SimilarityEngine", "SimilarityResult"]
