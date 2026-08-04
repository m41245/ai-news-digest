from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

router = APIRouter(
    prefix="/digests",
    tags=["Digests"],
)


@router.get("/")
async def list_digests() -> dict[str, list[Any]]:
    return {
        "digests": [],
    }


@router.get("/{digest_id}")
async def get_digest(
    digest_id: UUID,
) -> dict[str, Any]:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Digest {digest_id} not found.",
    )


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_digest() -> dict[str, str]:
    return {
        "message": "Digest generation has been queued.",
    }
