from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.enums.cluster_status import ClusterStatus
from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.infrastructure.database.models.story_cluster_model import (
    StoryClusterModel,
)


class StoryClusterMapper:
    """
    Maps between StoryCluster domain objects and StoryClusterModel ORM entities.
    """

    @staticmethod
    def to_model(cluster: StoryCluster) -> StoryClusterModel:
        """Convert a domain StoryCluster into a new ORM StoryClusterModel."""
        return StoryClusterModel(
            id=str(cluster.id),
            title=cluster.title,
            slug=cluster.slug,
            summary=cluster.summary,
            first_published_at=cluster.first_published_at,
            last_updated_at=cluster.last_updated_at,
            representative_article_id=(
                str(cluster.representative_article_id)
                if cluster.representative_article_id is not None
                else None
            ),
            latest_article_id=(
                str(cluster.latest_article_id)
                if cluster.latest_article_id is not None
                else None
            ),
            importance_score=cluster.importance_score,
            confidence=cluster.confidence,
            status=cluster.status.value,
        )

    @staticmethod
    def update_model(model: StoryClusterModel, cluster: StoryCluster) -> None:
        """Update an existing ORM model from a domain StoryCluster."""
        model.title = cluster.title
        model.slug = cluster.slug
        model.summary = cluster.summary
        model.first_published_at = cluster.first_published_at
        model.last_updated_at = cluster.last_updated_at
        model.representative_article_id = (
            str(cluster.representative_article_id)
            if cluster.representative_article_id is not None
            else None
        )
        model.latest_article_id = (
            str(cluster.latest_article_id)
            if cluster.latest_article_id is not None
            else None
        )
        model.importance_score = cluster.importance_score
        model.confidence = cluster.confidence
        model.status = cluster.status.value

    @staticmethod
    def to_domain(model: StoryClusterModel) -> StoryCluster:
        """Convert an ORM StoryClusterModel into a domain StoryCluster."""
        try:
            status = ClusterStatus(model.status)
        except ValueError:
            status = ClusterStatus.ACTIVE

        return StoryCluster(
            id=UUID(model.id),
            title=model.title,
            slug=model.slug,
            summary=model.summary,
            first_published_at=model.first_published_at,
            last_updated_at=model.last_updated_at,
            representative_article_id=(
                UUID(model.representative_article_id)
                if model.representative_article_id is not None
                else None
            ),
            latest_article_id=(
                UUID(model.latest_article_id)
                if model.latest_article_id is not None
                else None
            ),
            importance_score=model.importance_score,
            confidence=model.confidence,
            status=status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


__all__ = ["StoryClusterMapper"]
