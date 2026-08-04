from fastapi import APIRouter

from ai_news_digest.core.config import settings

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("")
async def health() -> dict[str, str]:
    """
    Basic health endpoint.

    Used by load balancers, Docker,
    Kubernetes and uptime monitoring.
    """
    return {
        "status": "healthy",
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@router.get("/ready")
async def readiness() -> dict[str, str]:
    """
    Readiness endpoint.

    Later this will verify:
    - PostgreSQL
    - Redis
    - Celery
    - LLM providers
    """
    return {
        "status": "ready",
    }
