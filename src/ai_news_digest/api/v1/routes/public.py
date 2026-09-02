"""
Public, unauthenticated API endpoints.

These routes expose a read-only, enriched view of articles, digests and
categories for the public product experience. No authentication is required.
Only processed articles (beyond NEW/FAILED) are surfaced.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.schemas.common import (
    DEFAULT_PAGE_LIMIT,
    MAX_OFFSET,
    MAX_PAGE_LIMIT,
    PaginatedResponse,
)
from ai_news_digest.api.v1.schemas.public import (
    PublicArticleResponse,
    PublicCategoryResponse,
    PublicDigestResponse,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.article import Article

router = APIRouter(
    prefix="/public",
    tags=["Public"],
)


async def _build_source_and_category_maps(
    container: Container,
) -> tuple[dict[UUID, str], dict[UUID, str]]:
    """Build id -> name lookup maps for sources and categories."""
    sources = await container.source_repository.list_all()
    categories = await container.category_repository.list_all()

    return (
        {source.id: source.name for source in sources},
        {category.id: category.name for category in categories},
    )


def _to_public_article(
    article: Article,
    source_map: dict[UUID, str],
    category_map: dict[UUID, str],
) -> PublicArticleResponse:
    return PublicArticleResponse(
        id=str(article.id),
        title=article.title,
        url=article.url,
        summary=article.summary,
        status=article.status.value,
        published_at=article.published_at.isoformat(),
        source_name=source_map.get(article.source_id),
        category_name=(category_map.get(article.category_id) if article.category_id else None),
    )


@router.get(
    "/articles",
    response_model=PaginatedResponse[PublicArticleResponse],
    summary="List public articles",
)
async def list_public_articles(
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
    category_id: Annotated[str | None, Query()] = None,
    source_id: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> PaginatedResponse[PublicArticleResponse]:
    """List publicly visible articles with optional filtering and search."""
    cat_id = UUID(category_id) if category_id else None
    src_id = UUID(source_id) if source_id else None

    source_map, category_map = await _build_source_and_category_maps(container)

    articles = await container.article_repository.list_public_articles(
        limit=limit,
        offset=offset,
        category_id=cat_id,
        source_id=src_id,
        search=search,
    )
    total = await container.article_repository.count_public_articles(
        category_id=cat_id,
        source_id=src_id,
        search=search,
    )

    return PaginatedResponse(
        items=[_to_public_article(a, source_map, category_map) for a in articles],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/articles/{article_id}",
    response_model=PublicArticleResponse,
    summary="Get a public article",
)
async def get_public_article(
    article_id: UUID,
    container: Annotated[Container, Depends(get_container)],
) -> PublicArticleResponse:
    """Retrieve a single public article by ID."""
    article = await container.article_repository.get_public_article(article_id)

    if article is None:
        raise ResourceNotFoundError(f"Article {article_id} not found.")

    source_map, category_map = await _build_source_and_category_maps(container)

    return _to_public_article(article, source_map, category_map)


@router.get(
    "/digests",
    response_model=PaginatedResponse[PublicDigestResponse],
    summary="List public digests",
)
async def list_public_digests(
    container: Annotated[Container, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
) -> PaginatedResponse[PublicDigestResponse]:
    """List publicly visible digests with pagination."""
    digests = await container.digest_repository.list_recent(limit=limit, offset=offset)
    total = await container.digest_repository.count()

    return PaginatedResponse(
        items=[
            PublicDigestResponse(
                id=str(digest.id),
                title=digest.title,
                content=digest.content,
                format=digest.format.value,
                generated_at=digest.generated_at.isoformat(),
                article_count=len(digest.article_ids),
            )
            for digest in digests
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/digests/{digest_id}",
    response_model=PublicDigestResponse,
    summary="Get a public digest",
)
async def get_public_digest(
    digest_id: UUID,
    container: Annotated[Container, Depends(get_container)],
) -> PublicDigestResponse:
    """Retrieve a single public digest by ID."""
    digest = await container.digest_repository.get_by_id(digest_id)

    if digest is None:
        raise ResourceNotFoundError(f"Digest {digest_id} not found.")

    return PublicDigestResponse(
        id=str(digest.id),
        title=digest.title,
        content=digest.content,
        format=digest.format.value,
        generated_at=digest.generated_at.isoformat(),
        article_count=len(digest.article_ids),
    )


@router.get(
    "/categories",
    response_model=list[PublicCategoryResponse],
    summary="List public categories",
)
async def list_public_categories(
    container: Annotated[Container, Depends(get_container)],
) -> list[PublicCategoryResponse]:
    """List all categories."""
    categories = await container.category_repository.list_all()

    return [
        PublicCategoryResponse(
            id=str(category.id),
            name=category.name,
            description=category.description,
        )
        for category in categories
    ]


__all__ = ["router"]
