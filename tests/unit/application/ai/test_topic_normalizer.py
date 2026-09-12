"""
Unit tests for topic normalization.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.ai.topic_normalizer import dedupe_topics, normalize_topic


class TestNormalizeTopic:
    def test_strips_whitespace(self) -> None:
        assert normalize_topic("  GPT  ") == "GPT"

    def test_collapses_internal_whitespace(self) -> None:
        assert normalize_topic("multi  modal\nmodels") == "multi modal models"

    def test_empty_returns_none(self) -> None:
        assert normalize_topic("") is None
        assert normalize_topic("   ") is None

    def test_single_word(self) -> None:
        assert normalize_topic("GPT") == "GPT"


class TestDedupeTopics:
    def test_removes_duplicates_case_insensitive(self) -> None:
        assert dedupe_topics(("GPT", "gpt")) == ("GPT",)

    def test_preserves_first_seen_casing(self) -> None:
        assert dedupe_topics(("gpt", "GPT")) == ("gpt",)

    def test_removes_empty(self) -> None:
        assert dedupe_topics(("GPT", "", "AI")) == ("GPT", "AI")

    def test_empty_input(self) -> None:
        assert dedupe_topics(()) == ()
        assert dedupe_topics(("", "  ")) == ()

    def test_limits_output(self) -> None:
        result = dedupe_topics(tuple(f"topic_{i}" for i in range(100)))
        assert len(result) == 100


__all__ = ["TestNormalizeTopic", "TestDedupeTopics"]
