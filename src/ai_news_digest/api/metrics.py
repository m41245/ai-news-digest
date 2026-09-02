from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ai_news_digest.api.v1.dependencies.auth import get_current_admin_user
from ai_news_digest.core.config import settings
from ai_news_digest.core.logging import get_logger
from ai_news_digest.core.metrics import (
    read_celery_metrics,
    record_ai_failure,
    record_ai_latency,
    record_article_collected,
    record_article_deduplicated,
    record_article_processed,
    record_celery_task_duration,
    record_celery_task_failure,
    record_celery_task_retry,
    record_celery_task_success,
    record_digest_generated,
    snapshot_application_metrics,
)
from ai_news_digest.infrastructure.database.session import get_pool_metrics

logger = get_logger(__name__)

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
)

_request_counts: dict[str, int] = defaultdict(int)
_request_latencies: dict[str, list[float]] = defaultdict(list)
_error_counts: dict[str, int] = defaultdict(int)
_lock = Lock()


def record_request(method: str, path: str, status_code: int, duration: float) -> None:
    """Record an HTTP request for metrics."""
    key = f"{method}:{path}"
    with _lock:
        _request_counts[key] += 1
        _request_latencies[key].append(duration)
        if len(_request_latencies[key]) > 1000:
            _request_latencies[key] = _request_latencies[key][-500:]
        if status_code >= 400:
            _error_counts[key] += 1


def _client_ip(request: Request) -> str | None:
    """Best-effort extraction of the originating client IP."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is not None:
        return request.client.host
    return None


def require_metrics_ip_access(
    request: Request,
) -> None:
    """Guard the metrics endpoint by an optional allow-list of client IPs.

    When ``settings.metrics_allowed_ips`` is non-empty, only requests whose
    resolved client IP is in the list are permitted. This provides defense in
    depth on top of the admin-authentication requirement, and is intended to
    restrict access to monitoring scrapers in production.
    """
    allowed = settings.metrics_allowed_ips
    if not allowed:
        return
    client_ip = _client_ip(request)
    if client_ip not in allowed:
        logger.warning(
            "Metrics endpoint access denied by IP allow-list",
            client_ip=client_ip,
        )
        raise HTTPException(
            status_code=403,
            detail="Access to metrics is not permitted from this address.",
        )


@router.get(
    "/",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_metrics_ip_access)],
)
async def metrics(
    request: Request,
    _: object = Depends(get_current_admin_user),
) -> Response:
    """
    Prometheus-style metrics endpoint.

    Exposes operational metrics for monitoring. This endpoint requires
    admin authentication and, when configured, an allowed client IP, and is
    not intended for public access. No secrets or user-identifiable data are
    exposed; only aggregate counters and durations are reported.
    """
    lines: list[str] = []

    with _lock:
        for key, count in _request_counts.items():
            lines.append(f'http_request_total{{route="{key}"}} {count}')

        for key, latencies in _request_latencies.items():
            if latencies:
                avg_latency = sum(latencies) / len(latencies)
                lines.append(
                    f'http_request_duration_avg_seconds{{route="{key}"}} {avg_latency:.4f}'
                )
                lines.append(f'http_request_duration_count{{route="{key}"}} {len(latencies)}')

        for key, count in _error_counts.items():
            lines.append(f'http_error_total{{route="{key}"}} {count}')

    app_metrics = snapshot_application_metrics()
    lines.append(f"articles_collected_total {app_metrics['articles_collected_total']}")
    lines.append(f"articles_processed_total {app_metrics['articles_processed_total']}")
    lines.append(f"articles_deduplicated_total {app_metrics['articles_deduplicated_total']}")
    lines.append(f"digests_generated_total {app_metrics['digests_generated_total']}")

    ai_failures = app_metrics["ai_provider_failures_total"]
    if not isinstance(ai_failures, dict):
        ai_failures = {}
    for provider, count in ai_failures.items():
        lines.append(f'ai_provider_failures_total{{provider="{provider}"}} {count}')

    ai_requests = app_metrics.get("ai_provider_requests_total", {})
    if not isinstance(ai_requests, dict):
        ai_requests = {}
    for provider, count in ai_requests.items():
        lines.append(f'ai_provider_requests_total{{provider="{provider}"}} {count}')

    ai_latencies = app_metrics["ai_processing_latencies"]
    if not isinstance(ai_latencies, dict):
        ai_latencies = {}
    for provider, samples in ai_latencies.items():
        if samples:
            avg = sum(samples) / len(samples)
            lines.append(f'ai_processing_duration_seconds{{provider="{provider}"}} {avg:.4f}')

    rss_success = app_metrics.get("rss_ingestion_success_total", {})
    if not isinstance(rss_success, dict):
        rss_success = {}
    for source, count in rss_success.items():
        lines.append(f'rss_ingestion_success_total{{source="{source}"}} {count}')

    rss_failure = app_metrics.get("rss_ingestion_failure_total", {})
    if not isinstance(rss_failure, dict):
        rss_failure = {}
    for source, count in rss_failure.items():
        lines.append(f'rss_ingestion_failure_total{{source="{source}"}} {count}')

    email_success = app_metrics.get("email_delivery_success_total", 0)
    lines.append(f"email_delivery_success_total {email_success}")

    email_failure = app_metrics.get("email_delivery_failure_total", 0)
    lines.append(f"email_delivery_failure_total {email_failure}")

    celery = await read_celery_metrics()
    lines.append(f"task_success_total {celery['task_success_total']:.0f}")
    lines.append(f"task_failure_total {celery['task_failure_total']:.0f}")
    lines.append(f"task_retries_total {celery['task_retries_total']:.0f}")
    if celery["task_duration_count"] > 0:
        avg_duration = celery["task_duration_sum"] / celery["task_duration_count"]
        lines.append(f"task_duration_seconds {avg_duration:.4f}")

    try:
        pool = get_pool_metrics()
        lines.append(f"db_pool_connections_active {pool['checkedout']}")
        lines.append(f"db_pool_connections_idle {pool['checkedin']}")
        lines.append(f"db_pool_overflow {pool['overflow']}")
    except Exception as exc:  # pragma: no cover - best effort metrics
        logger.debug("Failed to read database pool metrics: %s", exc)

    redis_connected = 0
    redis_store = getattr(request.app.state, "redis_store", None)
    if redis_store is not None:
        try:
            redis_connected = await redis_store.connectivity_metric()
        except Exception as exc:  # pragma: no cover - best effort metrics
            logger.debug("Failed to check Redis connectivity for metrics: %s", exc)
    lines.append(f"redis_connected {redis_connected}")

    return PlainTextResponse(
        content="\n".join(lines) + "\n" if lines else "",
        media_type="text/plain",
    )


@router.get("/health")
async def metrics_health() -> dict[str, str]:
    """Health check for the metrics endpoint itself."""
    return {"status": "ok"}


def _get_normalized_path(scope: Scope) -> str:
    """
    Return a low-cardinality path label for Prometheus metrics.

    Uses the resolved route's *template* path (e.g. ``/items/{id}``) so that
    dynamic segments do not explode the metric series. Falls back to a
    generic ``"unmatched"`` label when no route has been matched (e.g. 404s),
    preventing arbitrary request paths from creating unbounded series.
    """
    route = scope.get("route")
    if route is not None:
        path = getattr(route, "path", None)
        if path:
            return str(path)
    return "unmatched"


class MetricsMiddleware:
    """Middleware for collecting request metrics."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()
        method = scope.get("method", "GET")
        path = _get_normalized_path(scope)

        async def wrapped_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                duration = time.time() - start_time
                record_request(method, path, status_code, duration)
            await send(message)

        await self.app(scope, receive, wrapped_send)


__all__ = [
    "MetricsMiddleware",
    "record_ai_failure",
    "record_ai_latency",
    "record_article_collected",
    "record_article_deduplicated",
    "record_article_processed",
    "record_celery_task_duration",
    "record_celery_task_failure",
    "record_celery_task_retry",
    "record_celery_task_success",
    "record_digest_generated",
    "record_request",
    "router",
]
