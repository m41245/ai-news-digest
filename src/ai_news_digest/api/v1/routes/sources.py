from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/sources",
    tags=["Sources"],
)


# ---------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------


class SourceCreate(BaseModel):
    """
    Request model for creating a news source.
    """

    name: str = Field(..., min_length=1, max_length=200)
    url: str = Field(..., max_length=2048)
    category: str = Field(..., min_length=1, max_length=100)


class SourceResponse(BaseModel):
    """
    Response model representing a news source.
    """

    id: UUID
    name: str
    url: str
    category: str
    enabled: bool


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------


@router.get(
    "/",
    response_model=list[SourceResponse],
    summary="List news sources",
)
async def list_sources() -> list[SourceResponse]:
    """
    Return all configured news sources.

    Repository integration will be added later.
    """
    return []


@router.post(
    "/",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a news source",
)
async def create_source(
    source: SourceCreate,
) -> SourceResponse:
    """
    Create a new RSS source.

    Implementation will be added in a later milestone.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Source creation not implemented yet.",
    )


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a news source",
)
async def delete_source(
    source_id: UUID,
) -> None:
    """
    Delete a configured news source.

    Implementation will be added later.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Source deletion not implemented yet.",
    )
