"""
Category API endpoints.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from ai_news_digest.api.v1.dependencies.auth import get_current_active_user
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.application.use_cases.category.update import (
    UpdateCategoryRequest,
)
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.category import Category
from ai_news_digest.domain.models.user import User

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
)


class CategoryCreate(BaseModel):
    """Request model for creating a category."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field("", max_length=500)


class CategoryUpdate(BaseModel):
    """Request model for updating a category."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class CategoryReplace(BaseModel):
    """Request model for replacing a category."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field("", max_length=500)


class CategoryResponse(BaseModel):
    """Response model representing a category."""

    id: UUID
    name: str
    description: str | None = None


@router.get(
    "/",
    response_model=list[CategoryResponse],
    summary="List categories",
)
async def list_categories(
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> list[CategoryResponse]:
    """List all categories."""
    categories = await container.category_repository.list_all()

    return [
        CategoryResponse(
            id=category.id,
            name=category.name,
            description=category.description,
        )
        for category in categories
    ]


@router.get("/{category_id}", response_model=CategoryResponse, summary="Get category")
async def get_category(
    category_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CategoryResponse:
    """Retrieve a single category by ID."""
    category = await container.category_repository.get_by_id(category_id)

    if category is None:
        raise ResourceNotFoundError(f"Category {category_id} not found.")

    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
    )


@router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
)
async def create_category(
    category: CategoryCreate,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CategoryResponse:
    """Create a new category."""
    new_category = Category.create(
        name=category.name,
        description=category.description,
    )

    created = await container.category_repository.create(new_category)

    return CategoryResponse(
        id=created.id,
        name=created.name,
        description=created.description,
    )


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Delete category",
)
async def delete_category(
    category_id: UUID,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Delete a category by ID."""
    existing = await container.category_repository.get_by_id(category_id)

    if existing is None:
        raise ResourceNotFoundError(f"Category {category_id} not found.")

    await container.category_repository.delete(category_id)


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update category",
)
async def update_category(
    category_id: UUID,
    category_update: CategoryUpdate,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CategoryResponse:
    """Update an existing category."""
    request = UpdateCategoryRequest(
        id=category_id,
        name=category_update.name,
        description=category_update.description,
    )

    updated = await container.update_category.execute(request)

    return CategoryResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
    )


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Replace category",
)
async def replace_category(
    category_id: UUID,
    category_replace: CategoryReplace,
    container: Annotated[Container, Depends(get_container)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> CategoryResponse:
    """Replace an existing category."""
    request = UpdateCategoryRequest(
        id=category_id,
        name=category_replace.name,
        description=category_replace.description,
    )

    updated = await container.update_category.execute(request)

    return CategoryResponse(
        id=updated.id,
        name=updated.name,
        description=updated.description,
    )
