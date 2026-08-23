from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ai_news_digest.core.config import settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.infrastructure.cache.redis_store import RedisStore

logger = get_logger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("/live")
async def liveness() -> dict[str, str]:
    """
    Liveness endpoint.

    Used by Kubernetes to determine if the container needs restarting.
    This endpoint does not depend on external services.
    """
    return {
        "status": "alive",
        "application": settings.app_name,
    }


@router.get("/ready")
async def readiness() -> JSONResponse:
    """
    Readiness endpoint.

    Used by Kubernetes to determine if the container can accept traffic.
    Verifies connectivity to required dependencies: database and cache.

    Note: external AI providers (OpenAI, Anthropic) are intentionally not
    checked here. A temporary provider outage should not make the
    application appear dead.
    """
    checks: dict[str, str] = {}
    http_status = status.HTTP_200_OK

    try:
        from sqlalchemy.ext.asyncio import create_async_engine

        readiness_engine = create_async_engine(
            settings.database_url,
            pool_pre_ping=True,
            poolclass=None,
        )
        async with readiness_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
        await readiness_engine.dispose()
    except Exception as exc:
        logger.warning("readiness_check_failed", component="database", error=str(exc))
        checks["database"] = "unavailable"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        cache = settings.redis_url
        if cache:
            store = RedisStore(cache)
            await store.set("__readiness_probe__", "ok", ttl=10)
            await store.delete("__readiness_probe__")
        checks["cache"] = "ok"
    except Exception as exc:
        logger.warning("readiness_check_failed", component="cache", error=str(exc))
        checks["cache"] = "unavailable"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=http_status,
        content={
            "status": "ready" if http_status == 200 else "degraded",
            "application": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "checks": checks,
        },
    )


__all__ = ["router"]
