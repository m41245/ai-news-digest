from __future__ import annotations

from typing import TYPE_CHECKING

from ai_news_digest.application.dto.story_cluster import StoryClusterResponse

if TYPE_CHECKING:
    from ai_news_digest.domain.ports.story_cluster_repository import (
        StoryClusterRepository,
    )


class ListStoryClustersUseCase:
    """
    Application use case responsible for retrieving story clusters.
    """

    def __init__(
        self,
        repository: StoryClusterRepository,
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StoryClusterResponse]:
        """
        Retrieve story clusters ordered by first_published_at descending.
        """

        clusters = await self._repository.list_all(
            limit=limit,
            offset=offset,
        )

        return [
            StoryClusterResponse(
                id=str(cluster.id),
                title=cluster.title,
                slug=cluster.slug,
                summary=cluster.summary,
                first_published_at=cluster.first_published_at.isoformat(),
                last_updated_at=cluster.last_updated_at.isoformat(),
                representative_article_id=str(cluster.representative_article_id)
                if cluster.representative_article_id is not None
                else None,
                importance_score=cluster.importance_score,
                confidence=cluster.confidence,
                status=cluster.status.value,
            )
            for cluster in clusters
        ]
