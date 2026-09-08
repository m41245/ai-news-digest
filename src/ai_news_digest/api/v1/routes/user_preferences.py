"""
Authenticated user preference endpoints.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.common import (
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
)
from ai_news_digest.api.v1.schemas.user_preference import (
    UserPreferenceResponse,
    UserPreferenceUpdateRequest,
)
from ai_news_digest.application.dto.user_preference import (
    FeedSort,
    PersonalizedFeedResponse,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.domain.models.user import User

router = APIRouter(
    prefix="/me",
    tags=["User Preferences"],
)


@router.get(
    "/preferences",
    response_model=UserPreferenceResponse,
    summary="Get current user preferences",
)
async def get_preferences(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserPreferenceResponse:
    profile = await container.get_preferences.execute(current_user)
    return profile


@router.put(
    "/preferences",
    response_model=UserPreferenceResponse,
    summary="Update current user preferences",
)
async def update_preferences(
    request: UserPreferenceUpdateRequest,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserPreferenceResponse:
    return await container.update_preferences.execute(current_user, request)


@router.post(
    "/preferences/companies/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Follow a company",
)
async def follow_company(
    slug: str,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    company = await container.company_repository.get_by_slug(slug)
    if company is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Company '{slug}' not found.")
    await container.follow_company.execute(current_user, company.id)


@router.delete(
    "/preferences/companies/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Unfollow a company",
)
async def unfollow_company(
    slug: str,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    company = await container.company_repository.get_by_slug(slug)
    if company is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Company '{slug}' not found.")
    await container.unfollow_company.execute(current_user, company.id)


@router.post(
    "/preferences/topics/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Follow a topic",
)
async def follow_topic(
    slug: str,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    topic = await container.topic_repository.get_by_slug(slug)
    if topic is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Topic '{slug}' not found.")
    await container.follow_topic.execute(current_user, topic.id)


@router.delete(
    "/preferences/topics/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Unfollow a topic",
)
async def unfollow_topic(
    slug: str,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    topic = await container.topic_repository.get_by_slug(slug)
    if topic is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Topic '{slug}' not found.")
    await container.unfollow_topic.execute(current_user, topic.id)


@router.post(
    "/preferences/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Follow a category",
)
async def follow_category(
    category_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    category = await container.category_repository.get_by_id(category_id)
    if category is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Category '{category_id}' not found.")
    await container.follow_category.execute(current_user, category.id)


@router.delete(
    "/preferences/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Unfollow a category",
)
async def unfollow_category(
    category_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    category = await container.category_repository.get_by_id(category_id)
    if category is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Category '{category_id}' not found.")
    await container.unfollow_category.execute(current_user, category.id)


@router.post(
    "/preferences/muted/companies/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Mute a company",
)
async def mute_company(
    slug: str,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    company = await container.company_repository.get_by_slug(slug)
    if company is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Company '{slug}' not found.")
    await container.mute_company.execute(current_user, company.id)


@router.delete(
    "/preferences/muted/companies/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Unmute a company",
)
async def unmute_company(
    slug: str,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    company = await container.company_repository.get_by_slug(slug)
    if company is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Company '{slug}' not found.")
    await container.unmute_company.execute(current_user, company.id)


@router.post(
    "/preferences/muted/topics/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Mute a topic",
)
async def mute_topic(
    slug: str,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    topic = await container.topic_repository.get_by_slug(slug)
    if topic is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Topic '{slug}' not found.")
    await container.mute_topic.execute(current_user, topic.id)


@router.delete(
    "/preferences/muted/topics/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Unmute a topic",
)
async def unmute_topic(
    slug: str,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    topic = await container.topic_repository.get_by_slug(slug)
    if topic is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Topic '{slug}' not found.")
    await container.unmute_topic.execute(current_user, topic.id)


@router.post(
    "/preferences/muted/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Mute a category",
)
async def mute_category(
    category_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    category = await container.category_repository.get_by_id(category_id)
    if category is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Category '{category_id}' not found.")
    await container.mute_category.execute(current_user, category.id)


@router.delete(
    "/preferences/muted/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Unmute a category",
)
async def unmute_category(
    category_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    category = await container.category_repository.get_by_id(category_id)
    if category is None:
        from ai_news_digest.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError(f"Category '{category_id}' not found.")
    await container.unmute_category.execute(current_user, category.id)


@router.post(
    "/preferences/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Reset preferences to defaults",
)
async def reset_preferences(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    await container.reset_preferences.execute(current_user)


@router.get(
    "/feed",
    response_model=PersonalizedFeedResponse,
    summary="Get personalized feed",
)
async def get_feed(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    sort: Annotated[FeedSort, Query()] = "relevance",
    min_importance: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
    min_confidence: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
) -> PersonalizedFeedResponse:
    return await container.get_personalized_feed.execute(
        current_user=current_user,
        page=page,
        page_size=page_size,
        sort=sort,
        min_importance=min_importance,
        min_confidence=min_confidence,
    )


__all__ = ["router"]
