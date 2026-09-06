from __future__ import annotations

from typing import TYPE_CHECKING

from ai_news_digest.application.dto.story_cluster import (
    CreateStoryClusterRequest,
    StoryClusterResponse,
)
from ai_news_digest.domain.models.story_cluster import StoryCluster

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.story_cluster_repository import (
        StoryClusterRepository,
    )


class CreateStoryClusterUseCase:
    """
    Application use case responsible for creating a story cluster.
    """

    def __init__(
        self,
        repository: StoryClusterRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        request: CreateStoryClusterRequest,
    ) -> StoryClusterResponse:
        """
        Create a new story cluster.
        """

        cluster = StoryCluster.create(
            title=request.title,
            slug=request.slug,
            summary=request.summary,
        )

        created = await self._repository.create(cluster)

        return StoryClusterResponse(
            id=str(created.id),
            title=created.title,
            slug=created.slug,
            summary=created.summary,
            first_published_at=created.first_published_at.isoformat(),
            last_updated_at=created.last_updated_at.isoformat(),
            representative_article_id=str(created.representative_article_id)
            if created.representative_article_id is not None
            else None,
            importance_score=created.importance_score,
            confidence=created.confidence,
            status=created.status.value,
        )
