"""
Unit tests for M83 story activity domain models.
"""

from __future__ import annotations

import pytest
from uuid import uuid4

from ai_news_digest.domain.enums.story_activity_status import StoryActivityStatus
from ai_news_digest.domain.models.story_activity import StoryActivity


class TestStoryActivityStatus:
    def test_breaking_value(self) -> None:
        assert StoryActivityStatus.BREAKING.value == "breaking"

    def test_developing_value(self) -> None:
        assert StoryActivityStatus.DEVELOPING.value == "developing"

    def test_ongoing_value(self) -> None:
        assert StoryActivityStatus.ONGOING.value == "ongoing"

    def test_stale_value(self) -> None:
        assert StoryActivityStatus.STALE.value == "stale"

    def test_all_statuses(self) -> None:
        expected = {"breaking", "developing", "ongoing", "stale"}
        actual = {s.value for s in StoryActivityStatus}
        assert actual == expected


class TestStoryActivity:
    def test_create_breaking(self) -> None:
        from datetime import datetime, UTC

        activity = StoryActivity.create(
            story_cluster_id=uuid4(),
            status=StoryActivityStatus.BREAKING,
            activity_score=0.9,
            confidence=0.8,
            explanation="High velocity",
            evaluated_at=datetime.now(UTC),
            detection_version="v1",
            article_count_recent=10,
            unique_source_count_recent=7,
            recent_article_velocity=5.0,
        )
        assert activity.status == StoryActivityStatus.BREAKING
        assert activity.activity_score == 0.9
        assert activity.confidence == 0.8
        assert activity.article_count_recent == 10
        assert activity.unique_source_count_recent == 7

    def test_create_clamps_score(self) -> None:
        from datetime import datetime, UTC

        activity = StoryActivity.create(
            story_cluster_id=uuid4(),
            status=StoryActivityStatus.DEVELOPING,
            activity_score=1.5,
            confidence=0.5,
            explanation="Test",
            evaluated_at=datetime.now(UTC),
            detection_version="v1",
        )
        assert activity.activity_score == 1.0

        activity_low = StoryActivity.create(
            story_cluster_id=uuid4(),
            status=StoryActivityStatus.STALE,
            activity_score=-0.5,
            confidence=0.5,
            explanation="Test",
            evaluated_at=datetime.now(UTC),
            detection_version="v1",
        )
        assert activity_low.activity_score == 0.0

    def test_create_clamps_confidence(self) -> None:
        from datetime import datetime, UTC

        activity = StoryActivity.create(
            story_cluster_id=uuid4(),
            status=StoryActivityStatus.ONGOING,
            activity_score=0.5,
            confidence=1.5,
            explanation="Test",
            evaluated_at=datetime.now(UTC),
            detection_version="v1",
        )
        assert activity.confidence == 1.0

    def test_default_values(self) -> None:
        from datetime import datetime, UTC

        activity = StoryActivity.create(
            story_cluster_id=uuid4(),
            status=StoryActivityStatus.STALE,
            activity_score=0.0,
            confidence=0.0,
            explanation="No activity",
            evaluated_at=datetime.now(UTC),
            detection_version="v1",
        )
        assert activity.article_count_recent == 0
        assert activity.unique_source_count_recent == 0
        assert activity.recent_article_velocity == 0.0
        assert activity.latest_article_at is None
        assert activity.first_article_at is None
        assert activity.recent_claim_count == 0
        assert activity.recent_conflict_count == 0
        assert activity.state_change_count == 0


__all__ = ["TestStoryActivityStatus", "TestStoryActivity"]
