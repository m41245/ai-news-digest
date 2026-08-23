"""
Digest API endpoints.
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
from ai_news_digest.api.v1.schemas.delivery import DeliveryResponse
from ai_news_digest.api.v1.schemas.digest import (
    DigestCreate,
    DigestReplace,
    DigestResponse,
    DigestUpdate,
)
from ai_news_digest.application.use_cases.digest.update import (
    UpdateDigestRequest,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.exceptions import ResourceNotFoundError, ValidationError
from ai_news_digest.domain.models.user import User

router = APIRouter(
    prefix="/digests",
    tags=["Digests"],
)


@router.get("/", response_model=PaginatedResponse[DigestResponse], summary="List digests")
async def list_digests(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    offset: Annotated[int, Query(ge=0, le=MAX_OFFSET)] = 0,
) -> PaginatedResponse[DigestResponse]:
    """List digests with pagination."""
    digests = await container.digest_repository.list_recent(
        limit=limit,
        offset=offset,
    )
    total = await container.digest_repository.count()

    return PaginatedResponse(
        items=[
            DigestResponse(
                id=digest.id,
                title=digest.title,
                content=digest.content,
                format=digest.format,
                generated_at=digest.generated_at.isoformat(),
                article_ids=digest.article_ids,
            )
            for digest in digests
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{digest_id}", response_model=DigestResponse, summary="Get digest")
async def get_digest(
    digest_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> DigestResponse:
    """Retrieve a single digest by ID."""
    digest = await container.digest_repository.get_by_id(digest_id)

    if digest is None:
        raise ResourceNotFoundError(f"Digest {digest_id} not found.")

    return DigestResponse(
        id=digest.id,
        title=digest.title,
        content=digest.content,
        format=digest.format,
        generated_at=digest.generated_at.isoformat(),
        article_ids=digest.article_ids,
    )


@router.get(
    "/{digest_id}/deliveries",
    response_model=list[DeliveryResponse],
    summary="List digest deliveries",
)
async def list_digest_deliveries(
    digest_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> list[DeliveryResponse]:
    """Return delivery records for a digest."""
    digest = await container.digest_repository.get_by_id(digest_id)

    if digest is None:
        raise ResourceNotFoundError(f"Digest {digest_id} not found.")

    deliveries = await container.delivery_repository.list_by_digest(digest_id)

    return [
        DeliveryResponse(
            id=delivery.id,
            digest_id=delivery.digest_id,
            recipient=delivery.recipient,
            status=str(delivery.status),
            attempt_count=delivery.attempt_count,
            sent_at=delivery.sent_at,
            failed_at=delivery.failed_at,
            failure_reason=delivery.failure_reason,
            provider_message_id=delivery.provider_message_id,
            created_at=delivery.created_at,
        )
        for delivery in deliveries
    ]


@router.patch(
    "/{digest_id}",
    response_model=DigestResponse,
    summary="Update digest",
)
async def update_digest(
    digest_id: UUID,
    digest_update: DigestUpdate,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> DigestResponse:
    """Update an existing digest."""
    request = UpdateDigestRequest(
        id=digest_id,
        title=digest_update.title,
        content=digest_update.content,
        article_ids=digest_update.article_ids,
    )

    updated = await container.update_digest.execute(request)

    return DigestResponse(
        id=updated.id,
        title=updated.title,
        content=updated.content,
        format=updated.format,
        generated_at=updated.generated_at.isoformat(),
        article_ids=updated.article_ids,
    )


@router.put(
    "/{digest_id}",
    response_model=DigestResponse,
    summary="Replace digest",
)
async def replace_digest(
    digest_id: UUID,
    digest_replace: DigestReplace,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> DigestResponse:
    """Replace an existing digest."""
    request = UpdateDigestRequest(
        id=digest_id,
        title=digest_replace.title,
        content=digest_replace.content,
        article_ids=digest_replace.article_ids,
    )

    updated = await container.update_digest.execute(request)

    return DigestResponse(
        id=updated.id,
        title=updated.title,
        content=updated.content,
        format=updated.format,
        generated_at=updated.generated_at.isoformat(),
        article_ids=updated.article_ids,
    )


@router.post(
    "/generate",
    response_model=DigestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate digest",
)
async def generate_digest(
    request: DigestCreate,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> DigestResponse:
    """Trigger digest generation."""
    try:
        result = await container.generate_digest.execute(
            title=request.title,
            content=request.content,
            limit=request.limit,
        )

        digest = await container.digest_repository.get_by_id(result.digest_id)

        if digest is None:
            raise ResourceNotFoundError(f"Digest {result.digest_id} not found after creation.")

        return DigestResponse(
            id=digest.id,
            title=digest.title,
            content=digest.content,
            format=digest.format,
            generated_at=digest.generated_at.isoformat(),
            article_ids=digest.article_ids,
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


__all__ = ["router"]
