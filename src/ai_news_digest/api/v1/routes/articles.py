"""
Article API endpoints.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ai_news_digest.core.config import Settings, get_settings

router = APIRouter(
    prefix="/articles",
    tags=["Articles"],
)


@router.get("/")
async def list_articles(
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return {
        "items": [],
        "limit": limit,
        "offset": offset,
        "environment": settings.environment,
    }


@router.get("/{article_id}")
async def get_article(
    article_id: int,
) -> dict[str, Any]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Article retrieval is not implemented yet.",
    )
