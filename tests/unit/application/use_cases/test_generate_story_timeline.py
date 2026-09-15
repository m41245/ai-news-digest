from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from ai_news_digest.application.use_cases.story_timeline.generate_story_timeline import (
    GenerateStoryTimelineUseCase,
    _clamp,
    _compute_event_confidence,
    _event_fingerprint,
    _group_articles_by_event,
)
from ai_news_digest.domain.enums.cluster_status import ClusterStatus
from ai_news_digest.domain.enums.story_event_type import StoryEventType


def test_clamp() -> None:
    assert _clamp(0.5) == 0.5
    assert _clamp(1.5) == 1.0
    assert _clamp(-0.5) == 0.0


def test_event_fingerprint_deterministic() -> None:
    dt = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)
    fp1 = _event_fingerprint(StoryEventType.ANNOUNCEMENT, "Test", dt)
    fp2 = _event_fingerprint(StoryEventType.ANNOUNCEMENT, "Test", dt)
    assert fp1 == fp2


def test_group_articles_by_event() -> None:
    class FakeArticle:
        def __init__(self, title: str, published_at: datetime) -> None:
            self.title = title
            self.published_at = published_at
            self.source_id = uuid4()
            self.id = uuid4()

    articles = [
        FakeArticle(
            "OpenAI announcement GPT-5",
            datetime(2026, 9, 1, 8, 0, tzinfo=UTC),
        ),
    ]
    grouped = _group_articles_by_event(articles)
    assert len(grouped) == 1
    assert grouped[0][0] == StoryEventType.ANNOUNCEMENT


def test_compute_event_confidence() -> None:
    conf = _compute_event_confidence(
        article_count=3,
        distinct_source_count=2,
        has_claim_support=True,
    )
    assert 0.0 <= conf <= 1.0


@pytest.mark.asyncio
async def test_execute_disabled() -> None:
    from ai_news_digest.domain.models.story_cluster import StoryCluster

    cluster = StoryCluster(
        id=uuid4(),
        title="Test",
        slug="test",
        first_published_at=datetime(2026, 9, 1, tzinfo=UTC),
        last_updated_at=datetime(2026, 9, 1, tzinfo=UTC),
        status=ClusterStatus.ACTIVE,
    )
    cluster_repo = MagicMock()
    cluster_repo.get_by_id = AsyncMock(return_value=cluster)
    use_case = GenerateStoryTimelineUseCase(
        story_cluster_repository=cluster_repo,
        article_repository=MagicMock(),
        claim_repository=MagicMock(),
        conflict_repository=MagicMock(),
        story_activity_repository=MagicMock(),
        story_event_repository=MagicMock(),
        provider_manager=None,
    )
    use_case._settings = MagicMock()
    use_case._settings.timeline_generation_enabled = False
    result = await use_case.execute(cluster.id)
    assert result["status"] == "disabled"


@pytest.mark.asyncio
async def test_execute_cluster_not_found() -> None:
    cluster_repo = MagicMock()
    cluster_repo.get_by_id = AsyncMock(return_value=None)
    use_case = GenerateStoryTimelineUseCase(
        story_cluster_repository=cluster_repo,
        article_repository=MagicMock(),
        claim_repository=MagicMock(),
        conflict_repository=MagicMock(),
        story_activity_repository=MagicMock(),
        story_event_repository=MagicMock(),
        provider_manager=None,
    )
    use_case._settings = MagicMock()
    use_case._settings.timeline_generation_enabled = True
    with pytest.raises(ValueError, match="not found"):
        await use_case.execute(uuid4())


__all__ = [
    "test_clamp",
    "test_compute_event_confidence",
    "test_event_fingerprint_deterministic",
    "test_execute_cluster_not_found",
    "test_execute_disabled",
    "test_group_articles_by_event",
]
