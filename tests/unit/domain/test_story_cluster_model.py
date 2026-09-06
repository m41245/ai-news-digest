"""
Tests for the StoryCluster domain model.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ai_news_digest.domain.enums.cluster_status import ClusterStatus
from ai_news_digest.domain.models.story_cluster import StoryCluster


def test_story_cluster_creation():
    now = datetime.now(UTC)
    cluster = StoryCluster.create(
        title="OpenAI releases new model",
        slug="openai-releases-new-model",
        first_published_at=now,
    )
    assert isinstance(cluster.id, uuid4().__class__)
    assert cluster.title == "OpenAI releases new model"
    assert cluster.slug == "openai-releases-new-model"
    assert cluster.status == ClusterStatus.ACTIVE
    assert abs((cluster.created_at - now).total_seconds()) < 1
    assert abs((cluster.updated_at - now).total_seconds()) < 1
    assert abs((cluster.last_updated_at - now).total_seconds()) < 1


def test_story_cluster_touch():
    now = datetime.now(UTC)
    cluster = StoryCluster.create(
        title="Test",
        slug="test",
        first_published_at=now,
    )
    original_updated = cluster.updated_at
    cluster.touch()
    assert cluster.updated_at > original_updated
    assert cluster.last_updated_at == cluster.updated_at


def test_story_cluster_set_representative():
    article_id = uuid4()
    cluster = StoryCluster.create(
        title="Test",
        slug="test",
        representative_article_id=None,
    )
    cluster.set_representative(article_id)
    assert cluster.representative_article_id == article_id


def test_story_cluster_update_importance():
    cluster = StoryCluster.create(
        title="Test",
        slug="test",
    )
    cluster.update_importance(0.9, 0.85)
    assert cluster.importance_score == 0.9
    assert cluster.confidence == 0.85


def test_story_cluster_archive():
    cluster = StoryCluster.create(
        title="Test",
        slug="test",
    )
    assert cluster.status == ClusterStatus.ACTIVE
    cluster.archive()
    assert cluster.status == ClusterStatus.ARCHIVED


def test_story_cluster_merge_into():
    target_id = uuid4()
    cluster = StoryCluster.create(
        title="Test",
        slug="test",
    )
    cluster.merge_into(target_id)
    assert cluster.status == ClusterStatus.MERGED
