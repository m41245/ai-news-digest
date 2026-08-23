from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ai_news_digest.api.v1.dependencies.auth import get_current_admin_user
from ai_news_digest.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/metrics",
    tags=["Metrics"],
)

_request_counts: dict[str, int] = defaultdict(int)
_request_latencies: dict[str, list[float]] = defaultdict(list)
_error_counts: dict[str, int] = defaultdict(int)
_task_counts: dict[str, int] = defaultdict(int)
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


def record_task(task_name: str, success: bool) -> None:
    """Record a Celery task execution for metrics.

    Note: metrics are stored in-process (in-memory). When Celery workers run
    in separate containers/processes (as in the Docker Compose deployment),
    calls to this function update the worker's local memory and are not
    visible to the API server's ``/metrics`` endpoint. To expose task-level
    metrics across processes, a shared backend (e.g., Redis-backed counters or
    prometheus_client with a Push Gateway) would be required.
    """
    key = f"{task_name}:{'success' if success else 'failure'}"
    with _lock:
        _task_counts[key] += 1


@router.get("/", response_class=PlainTextResponse)
async def metrics(
    request: Request,
    _: object = Depends(get_current_admin_user),
) -> Response:
    """
    Prometheus-style metrics endpoint.

    Exposes operational metrics for monitoring. This endpoint requires
    admin authentication and is not intended for public access.
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

        for key, count in _task_counts.items():
            lines.append(f'task_total{{status="{key}"}} {count}')

    return PlainTextResponse(
        content="\n".join(lines) + "\n" if lines else "",
        media_type="text/plain",
    )


@router.get("/health")
async def metrics_health() -> dict[str, str]:
    """Health check for the metrics endpoint itself."""
    return {"status": "ok"}


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
        path = scope.get("path", "/")

        async def wrapped_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                duration = time.time() - start_time
                record_request(method, path, status_code, duration)
            await send(message)

        await self.app(scope, receive, wrapped_send)


__all__ = ["MetricsMiddleware", "record_request", "record_task", "router"]
