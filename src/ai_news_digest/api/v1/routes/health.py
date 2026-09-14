from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ai_news_digest.core.config import get_settings, settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.infrastructure.cache.redis_store import RedisStore
from ai_news_digest.infrastructure.database.session import engine

logger = get_logger(__name__)


def _fmt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


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


@router.get(
    "/notifications",
    summary="Notification system health check",
)
async def notification_health() -> dict[str, Any]:
    try:
        from ai_news_digest.bootstrap.container import Container
        from ai_news_digest.infrastructure.database.session import SessionLocal

        async with SessionLocal() as session:
            container = Container(session)
            delivery_repo = container.notification_delivery_repository
            pending = await delivery_repo.list_pending(limit=1)
            return {
                "status": "ok",
                "notification_system": "healthy",
                "pending_deliveries_sample": len(pending),
            }
    except Exception as exc:
        logger.error("Notification health check failed", error=str(exc))
        return {
            "status": "degraded",
            "notification_system": "unhealthy",
            "error": str(exc),
        }


@router.get(
    "/ai",
    summary="AI provider health check",
)
async def ai_health() -> dict[str, Any]:
    try:
        from ai_news_digest.bootstrap.container import Container
        from ai_news_digest.infrastructure.database.session import SessionLocal

        async with SessionLocal() as session:
            container = Container(session)
            providers = container.provider_registry.list_all()
            provider_statuses: dict[str, Any] = {}
            health_registry = container.provider_health_registry

            for provider in providers:
                status_info: dict[str, Any] = {
                    "name": provider.name,
                    "model": provider.model_name,
                    "configured": provider.enabled,
                }

                if health_registry is not None:
                    try:
                        health_state = await health_registry.get_state(provider.id)
                        is_eligible = await health_registry.is_eligible(provider.id)
                        status_info.update(
                            {
                                "circuit_state": health_state.state.value,
                                "available_for_routing": is_eligible,
                                "consecutive_failures": health_state.consecutive_failures,
                                "last_success": _fmt(health_state.last_success_at),
                                "last_failure": _fmt(health_state.last_failure_at),
                                "cooldown_until": _fmt(health_state.cooldown_until),
                            }
                        )
                    except Exception as exc:
                        try:
                            available = await provider.available()
                        except Exception:
                            available = False
                        status_info.update(
                            {
                                "circuit_state": "unknown",
                                "available_for_routing": available,
                                "error": str(exc),
                            }
                        )
                else:
                    try:
                        available = await provider.available()
                    except Exception as exc:
                        available = False
                        status_info.update(
                            {
                                "circuit_state": "unknown",
                                "available_for_routing": False,
                                "error": str(exc),
                            }
                        )
                    else:
                        status_info.update(
                            {
                                "circuit_state": "closed",
                                "available_for_routing": available,
                            }
                        )

                provider_statuses[provider.id] = status_info

            any_available = any(s.get("available_for_routing") for s in provider_statuses.values())
            return {
                "status": "ok" if any_available else "degraded",
                "ai_enabled": get_settings().ai_enabled,
                "providers": provider_statuses,
            }
    except Exception as exc:
        logger.error("AI health check failed", error=str(exc))
        return {
            "status": "degraded",
            "ai_enabled": get_settings().ai_enabled,
            "error": str(exc),
        }


__all__ = ["router"]
