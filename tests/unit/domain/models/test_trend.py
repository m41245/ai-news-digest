"""
Unit tests for M85 Trend domain model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ai_news_digest.domain.enums.trend_status import TrendStatus
from ai_news_digest.domain.enums.trend_type import TrendType
from ai_news_digest.domain.models.trend import Trend


class TestTrendCreate:
    def test_create_initializes_fields(self) -> None:
        now = datetime.now(UTC)
        trend = Trend.create(
            trend_type=TrendType.COMPANY_TREND,
            canonical_key="company:openai",
            display_name="OpenAI",
            status=TrendStatus.EMERGING,
            trend_score=75.0,
            momentum_score=80.0,
            first_detected_at=now,
            last_detected_at=now,
            recent_activity=14,
            baseline_activity=8,
            source_count=7,
            story_count=4,
            event_count=2,
            explanation="recent=14; baseline=8; growth=+0.75; sources=7",
        )
        assert trend.id is not None
        assert trend.trend_type == TrendType.COMPANY_TREND
        assert trend.canonical_key == "company:openai"
        assert trend.display_name == "OpenAI"
        assert trend.status == TrendStatus.EMERGING
        assert trend.trend_score == 75.0
        assert trend.momentum_score == 80.0
        assert trend.recent_activity == 14
        assert trend.baseline_activity == 8
        assert trend.source_count == 7
        assert trend.story_count == 4
        assert trend.event_count == 2

    def test_create_clamps_scores(self) -> None:
        now = datetime.now(UTC)
        trend = Trend.create(
            trend_type=TrendType.TOPIC_TREND,
            canonical_key="topic:llm",
            display_name="LLMs",
            status=TrendStatus.RISING,
            trend_score=150.0,
            momentum_score=-10.0,
            first_detected_at=now,
            last_detected_at=now,
            recent_activity=5,
            baseline_activity=3,
            source_count=4,
            story_count=2,
            event_count=1,
            explanation="test",
        )
        assert trend.trend_score == 100.0
        assert trend.momentum_score == 0.0

    def test_create_negative_activity_clamped_to_zero(self) -> None:
        now = datetime.now(UTC)
        trend = Trend.create(
            trend_type=TrendType.CATEGORY_TREND,
            canonical_key="category:research",
            display_name="Research",
            status=TrendStatus.STALE,
            trend_score=0.0,
            momentum_score=0.0,
            first_detected_at=now,
            last_detected_at=now,
            recent_activity=-5,
            baseline_activity=-3,
            source_count=0,
            story_count=0,
            event_count=0,
            explanation="test",
        )
        assert trend.recent_activity == 0
        assert trend.baseline_activity == 0


class TestTrendUpdate:
    def test_touch_updates_timestamps(self) -> None:
        now = datetime.now(UTC)
        trend = Trend.create(
            trend_type=TrendType.COMPANY_TREND,
            canonical_key="company:openai",
            display_name="OpenAI",
            status=TrendStatus.EMERGING,
            trend_score=75.0,
            momentum_score=80.0,
            first_detected_at=now,
            last_detected_at=now,
            recent_activity=14,
            baseline_activity=8,
            source_count=7,
            story_count=4,
            event_count=2,
            explanation="test",
        )
        original_updated = trend.updated_at
        trend.touch()
        assert trend.last_detected_at > now
        assert trend.updated_at >= trend.last_detected_at

    def test_update_scores_changes_status(self) -> None:
        now = datetime.now(UTC)
        trend = Trend.create(
            trend_type=TrendType.COMPANY_TREND,
            canonical_key="company:openai",
            display_name="OpenAI",
            status=TrendStatus.EMERGING,
            trend_score=75.0,
            momentum_score=80.0,
            first_detected_at=now,
            last_detected_at=now,
            recent_activity=14,
            baseline_activity=8,
            source_count=7,
            story_count=4,
            event_count=2,
            explanation="old",
        )
        trend.update_scores(
            trend_score=20.0,
            momentum_score=15.0,
            status=TrendStatus.COOLING,
            explanation="new",
        )
        assert trend.trend_score == 20.0
        assert trend.momentum_score == 15.0
        assert trend.status == TrendStatus.COOLING
        assert trend.explanation == "new"


__all__ = ["TestTrendCreate", "TestTrendUpdate"]
