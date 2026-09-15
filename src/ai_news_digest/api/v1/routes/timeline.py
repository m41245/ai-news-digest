from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends

from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.timeline import StoryEventResponse, StoryTimelineResponse
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.exceptions import ResourceNotFoundError

router = APIRouter(prefix="/story-clusters", tags=["Timeline"])


@router.get(
    "/{cluster_id}/timeline",
    response_model=StoryTimelineResponse,
    summary="Get story evolution timeline",
)
async def get_story_timeline(
    cluster_id: UUID,
    container: Container = Depends(get_container),
) -> StoryTimelineResponse:
    cluster = await container.story_cluster_repository.get_by_id(cluster_id)
    if cluster is None:
        raise ResourceNotFoundError(f"StoryCluster {cluster_id} not found")
    events = await container.story_event_repository.list_by_cluster_id(cluster_id)
    return StoryTimelineResponse(
        cluster_id=str(cluster_id),
        events=[
            StoryEventResponse(
                id=str(e.id),
                event_type=e.event_type.value,
                title=e.title,
                description=e.description,
                confidence=e.confidence,
                event_time=e.event_time.isoformat() if e.event_time else None,
                representative_article_id=(
                    str(e.representative_article_id)
                    if e.representative_article_id
                    else None
                ),
                sequence=e.sequence,
                article_count=len(e.article_ids),
                claim_count=len(e.claim_ids),
                processing_metadata=e.processing_metadata or None,
            )
            for e in events
        ],
        generated_at=datetime.now(UTC).isoformat(),
    )


__all__ = ["router"]
