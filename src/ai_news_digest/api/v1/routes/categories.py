from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
)


@router.get("/")
async def list_categories() -> dict[str, list[Any]]:
    return {
        "categories": [],
    }


@router.get("/{category_id}")
async def get_category(
    category_id: UUID,
) -> dict[str, Any]:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Category {category_id} not found.",
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_category() -> dict[str, str]:
    return {
        "message": "Category created successfully.",
    }


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Category deletion is not implemented yet.",
    )
