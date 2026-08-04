from fastapi import APIRouter, status

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get("/stats")
async def get_system_stats() -> dict[str, object]:
    """
    Return system statistics.

    Placeholder implementation.
    """

    return {
        "articles": 0,
        "sources": 0,
        "digests": 0,
        "status": "ok",
    }


@router.post(
    "/ingestion/run",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_ingestion() -> dict[str, str]:
    """
    Trigger the ingestion pipeline.

    Placeholder implementation.
    """

    return {
        "message": "Ingestion job has been queued.",
    }


@router.post(
    "/digest/run",
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_digest_generation() -> dict[str, str]:
    """
    Trigger digest generation.

    Placeholder implementation.
    """

    return {
        "message": "Digest generation job has been queued.",
    }


@router.post(
    "/cleanup",
    status_code=status.HTTP_202_ACCEPTED,
)
async def cleanup_database() -> dict[str, str]:
    """
    Trigger cleanup tasks.

    Placeholder implementation.
    """

    return {
        "message": "Cleanup job has been queued.",
    }


@router.get("/health")
async def admin_health() -> dict[str, str]:
    """
    Administrative health endpoint.
    """

    return {
        "status": "healthy",
        "service": "admin",
    }
