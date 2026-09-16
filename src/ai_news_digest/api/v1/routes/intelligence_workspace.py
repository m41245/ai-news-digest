"""
Authenticated intelligence workspace endpoints:
saved stories, user collections, and followed stories.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.common import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from ai_news_digest.api.v1.schemas.intelligence_workspace import (
    CollectionCreateRequest,
    CollectionResponse,
    CollectionUpdateRequest,
    FollowedStoryResponse,
    SavedStoryResponse,
    SaveStoryRequest,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.domain.models.followed_story import FollowedStory
from ai_news_digest.domain.models.saved_story import SavedStory
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.models.user_collection import UserCollection

router = APIRouter(
    prefix="/me",
    tags=["Intelligence Workspace"],
)


# ------------------------------------------------------------------
# Saved Stories
# ------------------------------------------------------------------


@router.post(
    "/saved-stories",
    response_model=SavedStoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a story cluster",
)
async def save_story(
    request: SaveStoryRequest,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> SavedStoryResponse:
    saved = await container.save_story.execute(
        user_id=current_user.id,
        story_cluster_id=UUID(request.story_cluster_id),
        collection_id=UUID(request.collection_id) if request.collection_id else None,
        note=request.note,
    )
    return _saved_story_to_response(saved)


@router.get(
    "/saved-stories",
    response_model=list[SavedStoryResponse],
    summary="List saved stories",
)
async def list_saved_stories(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    collection_id: str | None = Query(default=None),
    limit: int = Query(ge=1, le=MAX_PAGE_LIMIT, default=DEFAULT_PAGE_LIMIT),
    offset: int = Query(ge=0, default=0),
) -> list[SavedStoryResponse]:
    col_id = UUID(collection_id) if collection_id else None
    items, _ = await container.list_saved_stories.execute(
        user_id=current_user.id,
        collection_id=col_id,
        limit=limit,
        offset=offset,
    )
    return [_saved_story_to_response(item) for item in items]


@router.delete(
    "/saved-stories/{story_cluster_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Unsave a story",
)
async def unsave_story(
    story_cluster_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    await container.unsave_story.execute(
        user_id=current_user.id,
        story_cluster_id=story_cluster_id,
    )


# ------------------------------------------------------------------
# User Collections
# ------------------------------------------------------------------


@router.post(
    "/collections",
    response_model=CollectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a collection",
)
async def create_collection(
    request: CollectionCreateRequest,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CollectionResponse:
    collection = await container.create_collection.execute(
        user_id=current_user.id,
        name=request.name,
        description=request.description,
    )
    return _collection_to_response(collection)


@router.get(
    "/collections",
    response_model=list[CollectionResponse],
    summary="List collections",
)
async def list_collections(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = Query(ge=1, le=MAX_PAGE_LIMIT, default=DEFAULT_PAGE_LIMIT),
    offset: int = Query(ge=0, default=0),
) -> list[CollectionResponse]:
    items, _ = await container.list_collections.execute(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return [_collection_to_response(item) for item in items]


@router.patch(
    "/collections/{collection_id}",
    response_model=CollectionResponse,
    summary="Update a collection",
)
async def update_collection(
    collection_id: UUID,
    request: CollectionUpdateRequest,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CollectionResponse:
    collection = await container.update_collection.execute(
        user_id=current_user.id,
        collection_id=collection_id,
        name=request.name,
        description=request.description,
    )
    return _collection_to_response(collection)


@router.delete(
    "/collections/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete a collection",
)
async def delete_collection(
    collection_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    await container.delete_collection.execute(
        user_id=current_user.id,
        collection_id=collection_id,
    )


# ------------------------------------------------------------------
# Followed Stories
# ------------------------------------------------------------------


@router.post(
    "/followed-stories/{story_cluster_id}",
    response_model=FollowedStoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Follow a story cluster",
)
async def follow_story(
    story_cluster_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> FollowedStoryResponse:
    followed = await container.follow_story.execute(
        user_id=current_user.id,
        story_cluster_id=story_cluster_id,
    )
    return _followed_story_to_response(followed)


@router.delete(
    "/followed-stories/{story_cluster_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Unfollow a story cluster",
)
async def unfollow_story(
    story_cluster_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    await container.unfollow_story.execute(
        user_id=current_user.id,
        story_cluster_id=story_cluster_id,
    )


@router.get(
    "/followed-stories",
    response_model=list[FollowedStoryResponse],
    summary="List followed stories",
)
async def list_followed_stories(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = Query(ge=1, le=MAX_PAGE_LIMIT, default=DEFAULT_PAGE_LIMIT),
    offset: int = Query(ge=0, default=0),
) -> list[FollowedStoryResponse]:
    items, _ = await container.list_followed_stories.execute(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return [_followed_story_to_response(item) for item in items]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _saved_story_to_response(saved: SavedStory) -> SavedStoryResponse:
    return SavedStoryResponse(
        id=str(saved.id),
        user_id=str(saved.user_id),
        story_cluster_id=str(saved.story_cluster_id),
        collection_id=str(saved.collection_id) if saved.collection_id else None,
        note=saved.note,
        created_at=saved.created_at.isoformat() if saved.created_at else None,
    )


def _collection_to_response(collection: UserCollection) -> CollectionResponse:
    return CollectionResponse(
        id=str(collection.id),
        user_id=str(collection.user_id),
        name=collection.name,
        description=collection.description,
        created_at=collection.created_at.isoformat() if collection.created_at else None,
        updated_at=collection.updated_at.isoformat() if collection.updated_at else None,
    )


def _followed_story_to_response(followed: FollowedStory) -> FollowedStoryResponse:
    return FollowedStoryResponse(
        id=str(followed.id),
        user_id=str(followed.user_id),
        story_cluster_id=str(followed.story_cluster_id),
        created_at=followed.created_at.isoformat() if followed.created_at else None,
    )


__all__ = ["router"]
