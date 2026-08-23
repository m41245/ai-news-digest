"""
Article API endpoints.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.article import (
    ArticleCreate,
    ArticleResponse,
    ArticleUpdate,
)
from ai_news_digest.api.v1.schemas.common import (
    DEFAULT_PAGE_LIMIT,
    MAX_OFFSET,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
)
from ai_news_digest.application.dto.article import (
    CreateArticleRequest,
    UpdateArticleRequest,
)
from ai_news_digest.application.exceptions.article import ArticleNotFoundError
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.user import User

router = APIRouter(
    prefix="/articles",
    tags=["Articles"],
)


@router.post(
    "/",
    response_model=ArticleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an article",
)
async def create_article(
    article_create: ArticleCreate,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ArticleResponse:
    """Create a new article."""
    request = CreateArticleRequest(
        title=article_create.title,
        url=str(article_create.url),
        summary=article_create.summary,
        content=article_create.content,
        source_id=str(article_create.source_id),
        published_at=article_create.published_at.isoformat(),
        category_id=str(article_create.category_id) if article_create.category_id else None,
    )

    created = await container.create_article.execute(request)

    return ArticleResponse(
        id=created.id,
        title=created.title,
        url=created.url,
        summary=created.summary,
        content=created.content,
        status=created.status,
        published_at=created.published_at,
        fetched_at=created.fetched_at,
        source_id=created.source_id,
        category_id=created.category_id,
    )


@router.delete(
    "/{article_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete an article",
)
async def delete_article(
    article_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Delete an existing article."""
    try:
        await container.delete_article.execute(article_id)
    except ArticleNotFoundError:
        raise ResourceNotFoundError(f"Article {article_id} not found.") from None


@router.get("/", response_model=PaginatedResponse[ArticleResponse])
async def list_articles(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
) -> PaginatedResponse[ArticleResponse]:
    """List articles with pagination."""
    articles = await container.article_repository.list_recent(
        limit=limit,
        offset=offset,
    )
    total = await container.article_repository.count()

    return PaginatedResponse(
        items=[
            ArticleResponse(
                id=article.id,
                title=article.title,
                url=article.url,
                summary=article.summary,
                content=article.content,
                status=article.status,
                published_at=article.published_at,
                fetched_at=article.fetched_at,
                source_id=article.source_id,
                category_id=article.category_id,
            )
            for article in articles
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ArticleResponse:
    """Retrieve a single article by ID."""
    article = await container.article_repository.get_by_id(article_id)

    if article is None:
        raise ResourceNotFoundError(f"Article {article_id} not found.")

    return ArticleResponse(
        id=article.id,
        title=article.title,
        url=article.url,
        summary=article.summary,
        content=article.content,
        status=article.status,
        published_at=article.published_at,
        fetched_at=article.fetched_at,
        source_id=article.source_id,
        category_id=article.category_id,
    )


@router.patch(
    "/{article_id}",
    response_model=ArticleResponse,
    summary="Update an article",
)
async def update_article(
    article_id: UUID,
    article_update: ArticleUpdate,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> ArticleResponse:
    """Update an existing article."""
    request = UpdateArticleRequest(
        id=str(article_id),
        title=article_update.title,
        summary=article_update.summary,
        content=article_update.content,
        category_id=str(article_update.category_id) if article_update.category_id else None,
    )

    updated = await container.update_article.execute(request)

    return ArticleResponse(
        id=updated.id,
        title=updated.title,
        url=updated.url,
        summary=updated.summary,
        content=updated.content,
        status=updated.status,
        published_at=updated.published_at,
        fetched_at=updated.fetched_at,
        source_id=updated.source_id,
        category_id=updated.category_id,
    )


__all__ = ["router"]
