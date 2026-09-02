from __future__ import annotations

import time

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ai_news_digest.core.config import settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.infrastructure.cache.redis_store import RedisStore
from ai_news_digest.infrastructure.database.session import engine

logger = get_logger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)

_READINESS_CACHE_TTL = 5
_readiness_cache: dict[str, object] = {}


def _get_cached_readiness() -> tuple[dict[str, object], int] | None:
    cached = _readiness_cache.get("result")
    if not isinstance(cached, dict):
        return None
    cached_time = _readiness_cache.get("ts", 0)
    if not isinstance(cached_time, int | float):
        return None
    if time.time() - float(cached_time) > _READINESS_CACHE_TTL:
        _readiness_cache.clear()
        return None
    http_status = _readiness_cache.get("http_status", 200)
    if not isinstance(http_status, int):
        http_status = 200
    return cached, http_status


def _set_cached_readiness(payload: dict[str, object], http_status: int) -> None:
    _readiness_cache["result"] = payload
    _readiness_cache["ts"] = time.time()
    _readiness_cache["http_status"] = http_status


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
    cached = _get_cached_readiness()
    if cached is not None:
        payload, http_status = cached
        return JSONResponse(
            status_code=http_status,
            content=payload,
        )

    checks: dict[str, str] = {}
    http_status = status.HTTP_200_OK
    startup_time = getattr(settings, "app_startup_time", None)

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.warning("readiness_check_failed", component="database", error=str(exc))
        checks["database"] = "unavailable"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    try:
        cache_url = settings.redis_url
        if cache_url:
            store = RedisStore(cache_url)
            if not await store.ping():
                checks["cache"] = "unavailable"
                http_status = status.HTTP_503_SERVICE_UNAVAILABLE
            else:
                checks["cache"] = "ok"
        else:
            checks["cache"] = "ok"
    except Exception as exc:
        logger.warning("readiness_check_failed", component="cache", error=str(exc))
        checks["cache"] = "unavailable"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    payload = {
        "status": "ready" if http_status == 200 else "degraded",
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "checks": checks,
    }
    if startup_time is not None:
        payload["startup_time"] = startup_time

    _set_cached_readiness(payload, http_status)

    return JSONResponse(
        status_code=http_status,
        content=payload,
    )


__all__ = ["router"]
