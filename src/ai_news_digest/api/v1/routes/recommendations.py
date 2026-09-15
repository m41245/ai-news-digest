"""
Authenticated recommendation endpoints.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.common import (
    DEFAULT_PAGE_LIMIT,
    MAX_PAGE_LIMIT,
)
from ai_news_digest.api.v1.schemas.recommendation import (
    RecommendationResponse,
    RecommendationResponseWrapper,
    RecommendationSort,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.domain.models.user import User

router = APIRouter(
    prefix="/me",
    tags=["Recommendations"],
)


@router.get(
    "/recommendations",
    response_model=RecommendationResponseWrapper,
    summary="Get personalized recommendations",
)
async def get_recommendations(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    sort: Annotated[RecommendationSort, Query()] = "recommendation",
) -> RecommendationResponse:
    return await container.get_recommendations.execute(
        current_user=current_user,
        page=page,
        page_size=page_size,
        sort=sort,
    )


__all__ = ["router"]
