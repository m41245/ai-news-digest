"""
Source API endpoints.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.common import (
    DEFAULT_PAGE_LIMIT,
    MAX_OFFSET,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
)
from ai_news_digest.api.v1.schemas.source import (
    SourceCreate,
    SourceResponse,
    SourceUpdate,
)
from ai_news_digest.application.dto.source import UpdateSourceRequest
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.user import User

router = APIRouter(
    prefix="/sources",
    tags=["Sources"],
)


@router.get(
    "/",
    response_model=PaginatedResponse[SourceResponse],
    summary="List news sources",
)
async def list_sources(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
) -> PaginatedResponse[SourceResponse]:
    """Return all configured news sources with pagination."""
    sources = await container.source_repository.list_all(
        limit=limit,
        offset=offset,
    )
    total = await container.source_repository.count()

    return PaginatedResponse(
        items=[
            SourceResponse(
                id=source.id,
                name=source.name,
                feed_url=source.feed_url,
                website_url=source.website_url,
                description=source.description,
                is_active=source.is_active,
                status=source.status.value,
            )
            for source in sources
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a news source",
)
async def create_source(
    source: SourceCreate,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> SourceResponse:
    """Create a new RSS source."""
    from ai_news_digest.domain.models.source import Source

    new_source = Source.create(
        name=source.name,
        feed_url=source.feed_url,
        website_url=source.website_url,
        description=source.description,
    )

    created = await container.source_repository.create(new_source)

    return SourceResponse(
        id=created.id,
        name=created.name,
        feed_url=created.feed_url,
        website_url=created.website_url,
        description=created.description,
        is_active=created.is_active,
        status=created.status.value,
    )


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a news source",
)
async def delete_source(
    source_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Delete a configured news source."""
    existing = await container.source_repository.get_by_id(source_id)

    if existing is None:
        raise ResourceNotFoundError(f"Source {source_id} not found.")

    await container.source_repository.delete(source_id)


@router.patch(
    "/{source_id}",
    response_model=SourceResponse,
    summary="Update a news source",
)
async def update_source(
    source_id: UUID,
    source_update: SourceUpdate,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> SourceResponse:
    """Update an existing news source."""
    request = UpdateSourceRequest(
        id=source_id,
        name=source_update.name,
        feed_url=source_update.feed_url,
        website_url=source_update.website_url,
        description=source_update.description,
        is_active=source_update.is_active,
    )

    updated = await container.update_source.execute(request)

    return SourceResponse(
        id=updated.id,
        name=updated.name,
        feed_url=updated.feed_url,
        website_url=updated.website_url,
        description=updated.description,
        is_active=updated.is_active,
        status=updated.status,
    )


__all__ = ["router"]
