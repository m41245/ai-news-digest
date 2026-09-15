"""Unit tests for SimilarityEngine."""
from __future__ import annotations

import math

import pytest

from ai_news_digest.application.ai.similarity_engine import SimilarityEngine


@pytest.fixture
def engine() -> SimilarityEngine:
    return SimilarityEngine()


class TestCosineSimilarity:
    def test_identical_vectors(self, engine: SimilarityEngine) -> None:
        v = (1.0, 2.0, 3.0)
        result = engine.cosine_similarity(v, v)
        assert result.is_valid is True
        assert math.isclose(result.score, 1.0, rel_tol=1e-9)

    def test_orthogonal_vectors(self, engine: SimilarityEngine) -> None:
        a = (1.0, 0.0)
        b = (0.0, 1.0)
        result = engine.cosine_similarity(a, b)
        assert result.is_valid is True
        assert math.isclose(result.score, 0.0, abs_tol=1e-9)

    def test_opposite_vectors(self, engine: SimilarityEngine) -> None:
        a = (1.0, 2.0)
        b = (-1.0, -2.0)
        result = engine.cosine_similarity(a, b)
        assert result.is_valid is True
        assert math.isclose(result.score, -1.0, rel_tol=1e-9)

    def test_zero_vector_a(self, engine: SimilarityEngine) -> None:
        result = engine.cosine_similarity((0.0, 0.0), (1.0, 2.0))
        assert result.is_valid is True
        assert result.score == 0.0
        assert result.error == "Zero magnitude vector"

    def test_zero_vector_b(self, engine: SimilarityEngine) -> None:
        result = engine.cosine_similarity((1.0, 2.0), (0.0, 0.0))
        assert result.is_valid is True
        assert result.score == 0.0

    def test_dimension_mismatch(self, engine: SimilarityEngine) -> None:
        result = engine.cosine_similarity((1.0, 2.0), (1.0, 2.0, 3.0))
        assert result.is_valid is False
        assert result.score == 0.0
        assert "Dimension mismatch" in result.error

    def test_empty_vectors(self, engine: SimilarityEngine) -> None:
        result = engine.cosine_similarity((), ())
        assert result.is_valid is False
        assert result.score == 0.0
        assert result.error == "Empty vectors"

    def test_normalized_similarity_negative_clamped(self, engine: SimilarityEngine) -> None:
        a = (1.0, 0.0)
        b = (-1.0, 0.0)
        score = engine.normalized_similarity(a, b)
        assert score == 0.0

    def test_partial_overlap(self, engine: SimilarityEngine) -> None:
        a = (1.0, 0.0, 0.0)
        b = (1.0, 1.0, 0.0)
        result = engine.cosine_similarity(a, b)
        assert result.is_valid is True
        expected = 1.0 / math.sqrt(2.0)
        assert math.isclose(result.score, expected, rel_tol=1e-9)
