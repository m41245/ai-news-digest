from __future__ import annotations

import contextlib
from collections import defaultdict
from threading import Lock

import redis.asyncio as aioredis

from ai_news_digest.core.config import settings
from ai_news_digest.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# In-process application metrics
# ---------------------------------------------------------------------------
# These counters are scoped to a single process. They capture application-level
# activity (articles collected/processed, digests generated, AI provider
# failures/latency) and are exposed by the API server's /metrics endpoint.

_articles_collected_total = 0
_articles_processed_total = 0
_articles_deduplicated_total = 0
_digests_generated_total = 0

_ai_provider_failures_total: dict[str, int] = defaultdict(int)
_ai_processing_latencies: dict[str, list[float]] = defaultdict(list)
_ai_provider_requests_total: dict[str, int] = defaultdict(int)

_rss_ingestion_success_total: dict[str, int] = defaultdict(int)
_rss_ingestion_failure_total: dict[str, int] = defaultdict(int)

_email_delivery_success_total = 0
_email_delivery_failure_total = 0

_lock = Lock()

_MAX_LATENCY_SAMPLES = 1000


def record_article_collected(count: int = 1) -> None:
    """Increment the count of articles collected from sources."""
    global _articles_collected_total
    if count <= 0:
        return
    with _lock:
        _articles_collected_total += count


def record_article_processed(count: int = 1) -> None:
    """Increment the count of articles processed by the AI pipeline."""
    global _articles_processed_total
    if count <= 0:
        return
    with _lock:
        _articles_processed_total += count


def record_article_deduplicated(count: int = 1) -> None:
    """Increment the count of articles discarded as duplicates."""
    global _articles_deduplicated_total
    if count <= 0:
        return
    with _lock:
        _articles_deduplicated_total += count


def record_digest_generated(count: int = 1) -> None:
    """Increment the count of digests generated."""
    global _digests_generated_total
    if count <= 0:
        return
    with _lock:
        _digests_generated_total += count


def record_ai_failure(provider: str) -> None:
    """Record a failure for the given AI provider."""
    if not provider:
        provider = "unknown"
    with _lock:
        _ai_provider_failures_total[provider] += 1


def record_ai_latency(provider: str, duration_seconds: float) -> None:
    """Record AI provider processing latency (in seconds) for a request."""
    if not provider:
        provider = "unknown"
    if duration_seconds < 0:
        return
    with _lock:
        samples = _ai_processing_latencies[provider]
        samples.append(duration_seconds)
        if len(samples) > _MAX_LATENCY_SAMPLES:
            del samples[: len(samples) - (_MAX_LATENCY_SAMPLES // 2)]


def record_ai_request(provider: str) -> None:
    """Record an AI provider request."""
    if not provider:
        provider = "unknown"
    with _lock:
        _ai_provider_requests_total[provider] += 1


def record_rss_ingestion_success(source: str) -> None:
    """Record a successful RSS ingestion for a source."""
    if not source:
        source = "unknown"
    with _lock:
        _rss_ingestion_success_total[source] += 1


def record_rss_ingestion_failure(source: str) -> None:
    """Record a failed RSS ingestion for a source."""
    if not source:
        source = "unknown"
    with _lock:
        _rss_ingestion_failure_total[source] += 1


def record_email_delivery_success(count: int = 1) -> None:
    """Record successful email deliveries."""
    global _email_delivery_success_total
    if count <= 0:
        return
    with _lock:
        _email_delivery_success_total += count


def record_email_delivery_failure(count: int = 1) -> None:
    """Record failed email deliveries."""
    global _email_delivery_failure_total
    if count <= 0:
        return
    with _lock:
        _email_delivery_failure_total += count


def snapshot_application_metrics() -> dict[str, object]:
    """Return a copy of the current application-level metric values."""
    with _lock:
        return {
            "articles_collected_total": _articles_collected_total,
            "articles_processed_total": _articles_processed_total,
            "articles_deduplicated_total": _articles_deduplicated_total,
            "digests_generated_total": _digests_generated_total,
            "ai_provider_failures_total": dict(_ai_provider_failures_total),
            "ai_provider_requests_total": dict(_ai_provider_requests_total),
            "ai_processing_latencies": {
                provider: list(samples) for provider, samples in _ai_processing_latencies.items()
            },
            "rss_ingestion_success_total": dict(_rss_ingestion_success_total),
            "rss_ingestion_failure_total": dict(_rss_ingestion_failure_total),
            "email_delivery_success_total": _email_delivery_success_total,
            "email_delivery_failure_total": _email_delivery_failure_total,
        }


# ---------------------------------------------------------------------------
# Cross-process Celery metrics (Redis-backed)
# ---------------------------------------------------------------------------
# Celery workers run in separate processes/containers, so in-memory counters
# are not visible to the API server. These helpers persist task counters in
# Redis so they can be aggregated and exposed by the /metrics endpoint
# regardless of which process emitted them. All helpers fail silently: a
# metrics outage must never break a task.

_METRICS_KEY_PREFIX = "ai_news_digest:metrics:"

CELERY_SUCCESS_KEY = _METRICS_KEY_PREFIX + "celery:task_success_total"
CELERY_FAILURE_KEY = _METRICS_KEY_PREFIX + "celery:task_failure_total"
CELERY_RETRIES_KEY = _METRICS_KEY_PREFIX + "celery:task_retries_total"
CELERY_DURATION_SUM_KEY = _METRICS_KEY_PREFIX + "celery:task_duration_sum"
CELERY_DURATION_COUNT_KEY = _METRICS_KEY_PREFIX + "celery:task_duration_count"


def _build_redis_client(
    redis_url: str | None = None,
) -> aioredis.Redis:
    """Build a lightweight Redis client for metrics writes/reads."""
    url = redis_url or settings.redis_url
    client: aioredis.Redis = aioredis.from_url(  # type: ignore[no-untyped-call]
        url,
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=True,
    )
    return client


async def record_celery_task_success(
    task_name: str,
    *,
    redis_url: str | None = None,
) -> None:
    """Increment the cross-process success counter for a Celery task."""
    await _safe_incr(CELERY_SUCCESS_KEY, redis_url)


async def record_celery_task_failure(
    task_name: str,
    *,
    redis_url: str | None = None,
) -> None:
    """Increment the cross-process failure counter for a Celery task."""
    await _safe_incr(CELERY_FAILURE_KEY, redis_url)


async def record_celery_task_retry(
    task_name: str,
    *,
    redis_url: str | None = None,
) -> None:
    """Increment the cross-process retry counter for a Celery task."""
    await _safe_incr(CELERY_RETRIES_KEY, redis_url)


async def record_celery_task_duration(
    task_name: str,
    duration_seconds: float,
    *,
    redis_url: str | None = None,
) -> None:
    """Add a duration sample (in seconds) to the cross-process task timer."""
    if duration_seconds < 0:
        return
    client = _build_redis_client(redis_url)
    try:
        await client.incrbyfloat(CELERY_DURATION_SUM_KEY, duration_seconds)
        await client.incr(CELERY_DURATION_COUNT_KEY)
    except Exception as exc:  # pragma: no cover - best effort metrics
        logger.debug("Failed to record Celery task duration: %s", exc)
    finally:
        with contextlib.suppress(Exception):
            await client.aclose()


async def _safe_incr(key: str, redis_url: str | None) -> None:
    client = _build_redis_client(redis_url)
    try:
        await client.incr(key)
    except Exception as exc:  # pragma: no cover - best effort metrics
        logger.debug("Failed to increment Redis metric %s: %s", key, exc)
    finally:
        with contextlib.suppress(Exception):
            await client.aclose()


async def read_celery_metrics(
    *,
    redis_url: str | None = None,
) -> dict[str, float]:
    """Read the current cross-process Celery metric totals from Redis."""
    client = _build_redis_client(redis_url)
    try:
        raw = await client.mget(
            CELERY_SUCCESS_KEY,
            CELERY_FAILURE_KEY,
            CELERY_RETRIES_KEY,
            CELERY_DURATION_SUM_KEY,
            CELERY_DURATION_COUNT_KEY,
        )
        success, failure, retries, duration_sum, duration_count = (
            raw[0],
            raw[1],
            raw[2],
            raw[3],
            raw[4],
        )
        return {
            "task_success_total": float(success) if success is not None else 0.0,
            "task_failure_total": float(failure) if failure is not None else 0.0,
            "task_retries_total": float(retries) if retries is not None else 0.0,
            "task_duration_sum": float(duration_sum) if duration_sum is not None else 0.0,
            "task_duration_count": float(duration_count) if duration_count is not None else 0.0,
        }
    except Exception as exc:  # pragma: no cover - best effort metrics
        logger.debug("Failed to read Redis Celery metrics: %s", exc)
        return {
            "task_success_total": 0.0,
            "task_failure_total": 0.0,
            "task_retries_total": 0.0,
            "task_duration_sum": 0.0,
            "task_duration_count": 0.0,
        }
    finally:
        with contextlib.suppress(Exception):
            await client.aclose()


__all__ = [
    "CELERY_DURATION_COUNT_KEY",
    "CELERY_DURATION_SUM_KEY",
    "CELERY_FAILURE_KEY",
    "CELERY_RETRIES_KEY",
    "CELERY_SUCCESS_KEY",
    "read_celery_metrics",
    "record_ai_failure",
    "record_ai_latency",
    "record_ai_request",
    "record_article_collected",
    "record_article_deduplicated",
    "record_article_processed",
    "record_celery_task_duration",
    "record_celery_task_failure",
    "record_celery_task_retry",
    "record_celery_task_success",
    "record_digest_generated",
    "record_email_delivery_failure",
    "record_email_delivery_success",
    "record_rss_ingestion_failure",
    "record_rss_ingestion_success",
    "snapshot_application_metrics",
]
