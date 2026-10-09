from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncIterator
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol, cast

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from ai_news_digest.application.ai.provider_health import utc_now
from ai_news_digest.application.ai.provider_quota_registry import ProviderQuotaRegistry
from ai_news_digest.application.ai.quota import (
    GlobalBudgetState,
    ProviderQuotaConfig,
    ProviderUsage,
    QuotaEligibility,
    QuotaLimit,
    QuotaReservationRequest,
    QuotaReservationResult,
    QuotaWindow,
    ReleaseResult,
    ReservationState,
    ReservationStatus,
    SettlementResult,
)
from ai_news_digest.core.config import settings
from ai_news_digest.core.logging import get_logger

logger = get_logger(__name__)

_NAMESPACE = "ai:provider-quota"
_BUDGET_NAMESPACE = "ai:budget"
_USAGE_TTL_SECONDS = 2592000
_RESERVATION_TTL_SECONDS = (
    604800  # 7 days — long enough for the 15-minute reconciliation task to expire + release
)
_RESERVATION_EXPIRED_TTL_SECONDS = 604800  # 7 days for expired reservations to allow recovery
_RESERVATION_PATTERN = f"{_NAMESPACE}:reservation:*"


def _provider_quota_key(provider_id: str) -> str:
    return f"{_NAMESPACE}:{provider_id}"


def _provider_usage_key(provider_id: str, window: QuotaWindow) -> str:
    return f"{_NAMESPACE}:{provider_id}:usage:{window.value}"


def _global_budget_key() -> str:
    return f"{_BUDGET_NAMESPACE}:global"


def _reservation_key(reservation_id: str) -> str:
    return f"{_NAMESPACE}:reservation:{reservation_id}"


def _window_id(window: QuotaWindow, now: datetime | None = None) -> str:
    now = now or utc_now()
    if window == QuotaWindow.MINUTE:
        return now.strftime("%Y%m%d%H%M")
    if window == QuotaWindow.HOUR:
        return now.strftime("%Y%m%d%H")
    if window == QuotaWindow.DAY:
        return now.strftime("%Y%m%d")
    if window == QuotaWindow.MONTH:
        return now.strftime("%Y%m")
    raise ValueError(f"Unknown QuotaWindow: {window}")


_RECORD_USAGE_LUA = """
local key = KEYS[1]
local now = ARGV[1]
local req_count = tonumber(ARGV[2])
local input_tokens = tonumber(ARGV[3])
local output_tokens = tonumber(ARGV[4])
local total_tokens = tonumber(ARGV[5])
local cost = tonumber(ARGV[6])

local current_req = tonumber(redis.call("HGET", key, "request_count") or "0")
local current_input = tonumber(redis.call("HGET", key, "input_tokens") or "0")
local current_output = tonumber(redis.call("HGET", key, "output_tokens") or "0")
local current_total = tonumber(redis.call("HGET", key, "total_tokens") or "0")
local current_cost = tonumber(redis.call("HGET", key, "estimated_cost") or "0")

redis.call("HSET", key,
    "request_count", tostring(current_req + req_count),
    "input_tokens", tostring(current_input + input_tokens),
    "output_tokens", tostring(current_output + output_tokens),
    "total_tokens", tostring(current_total + total_tokens),
    "estimated_cost", tostring(current_cost + cost),
    "updated_at", now
)
redis.call("EXPIRE", key, tonumber(ARGV[7]))
return redis.call("HGETALL", key)
"""


_CHECK_QUOTA_LUA = """
local key = KEYS[1]
local req_limit = tonumber(ARGV[1])
local token_limit = tonumber(ARGV[2])
local cost_limit = tonumber(ARGV[3])
local est_tokens = tonumber(ARGV[4])
local est_cost = tonumber(ARGV[5])

local current_req = tonumber(redis.call("HGET", key, "request_count") or "0")
local current_tokens = tonumber(redis.call("HGET", key, "total_tokens") or "0")
local current_cost = tonumber(redis.call("HGET", key, "estimated_cost") or "0")
local reserved_req = tonumber(redis.call("HGET", key, "reserved_requests") or "0")
local reserved_tokens = tonumber(redis.call("HGET", key, "reserved_total_tokens") or "0")
local reserved_cost = tonumber(redis.call("HGET", key, "reserved_cost") or "0")

if req_limit ~= nil and req_limit >= 0 and (current_req + reserved_req) >= req_limit then
    return "request_exhausted"
end
if token_limit ~= nil and token_limit >= 0 and (current_tokens + reserved_tokens + est_tokens) > token_limit then
    return "token_exhausted"
end
if cost_limit ~= nil and cost_limit >= 0 and (current_cost + reserved_cost + est_cost) > cost_limit then
    return "cost_exhausted"
end
return "eligible"
"""


_RESERVE_CAPACITY_LUA = """
local usage_key = KEYS[1]
local budget_key = KEYS[2]
local res_key = KEYS[3]

local req_count = tonumber(ARGV[1])
local input_tokens = tonumber(ARGV[2])
local output_tokens = tonumber(ARGV[3])
local total_tokens = tonumber(ARGV[4])
local est_cost = tonumber(ARGV[5])
local req_limit = tonumber(ARGV[6])
local token_limit = tonumber(ARGV[7])
local cost_limit = tonumber(ARGV[8])
local daily_budget = tonumber(ARGV[9])
local monthly_budget = tonumber(ARGV[10])
local reservation_id = ARGV[11]
local provider_id = ARGV[12]
local window = ARGV[13]
local now = ARGV[14]
local ttl = tonumber(ARGV[15])

-- Idempotency: if reservation already exists, do not double-count
local existing_status = redis.call("HGET", res_key, "status") or "none"
if existing_status == "pending" then
    return "already_reserved"
end
if existing_status == "settled" then
    return "already_settled"
end
if existing_status == "released" then
    return "already_released"
end
if existing_status == "expired" then
    return "already_expired"
end

local current_req = tonumber(redis.call("HGET", usage_key, "request_count") or "0")
local current_total = tonumber(redis.call("HGET", usage_key, "total_tokens") or "0")
local current_cost = tonumber(redis.call("HGET", usage_key, "estimated_cost") or "0")
local reserved_req = tonumber(redis.call("HGET", usage_key, "reserved_requests") or "0")
local reserved_tokens = tonumber(redis.call("HGET", usage_key, "reserved_total_tokens") or "0")
local reserved_cost = tonumber(redis.call("HGET", usage_key, "reserved_cost") or "0")

if req_limit >= 0 and (current_req + reserved_req + req_count) > req_limit then
    return "request_exhausted"
end
if token_limit >= 0 and (current_total + reserved_tokens + total_tokens) > token_limit then
    return "token_exhausted"
end
if cost_limit >= 0 and (current_cost + reserved_cost + est_cost) > cost_limit then
    return "cost_exhausted"
end

local budget_exists = redis.call("EXISTS", budget_key)
if daily_budget > 0 and budget_exists == 1 then
    local daily_spend = tonumber(redis.call("HGET", budget_key, "daily_spend") or "0")
    local reserved_daily = tonumber(redis.call("HGET", budget_key, "reserved_daily_cost") or "0")
    if (daily_spend + reserved_daily + est_cost) > daily_budget then
        return "daily_budget_exhausted"
    end
end

if monthly_budget > 0 and budget_exists == 1 then
    local monthly_spend = tonumber(redis.call("HGET", budget_key, "monthly_spend") or "0")
    local reserved_monthly = tonumber(redis.call("HGET", budget_key, "reserved_monthly_cost") or "0")
    if (monthly_spend + reserved_monthly + est_cost) > monthly_budget then
        return "monthly_budget_exhausted"
    end
end

-- All checks passed --
redis.call("HINCRBY", usage_key, "reserved_requests", req_count)
redis.call("HINCRBY", usage_key, "reserved_input_tokens", input_tokens)
redis.call("HINCRBY", usage_key, "reserved_output_tokens", output_tokens)
redis.call("HINCRBY", usage_key, "reserved_total_tokens", total_tokens)
redis.call("HINCRBYFLOAT", usage_key, "reserved_cost", est_cost)
redis.call("HSET", usage_key, "updated_at", now)
redis.call("EXPIRE", usage_key, ttl)

if budget_exists == 1 and (daily_budget > 0 or monthly_budget > 0) then
    redis.call("HINCRBYFLOAT", budget_key, "reserved_daily_cost", est_cost)
    redis.call("HINCRBYFLOAT", budget_key, "reserved_monthly_cost", est_cost)
    redis.call("HSET", budget_key, "updated_at", now)
    redis.call("EXPIRE", budget_key, ttl)
end

redis.call("HMSET", res_key,
    "reservation_id", reservation_id,
    "provider_id", provider_id,
    "window", window,
    "request_count", tostring(req_count),
    "input_tokens", tostring(input_tokens),
    "output_tokens", tostring(output_tokens),
    "total_tokens", tostring(total_tokens),
    "estimated_cost", tostring(est_cost),
    "status", "pending",
    "created_at", now,
    "updated_at", now
)
redis.call("EXPIRE", res_key, ttl)

return "reserved"
"""


_SETTLE_RESERVATION_LUA = """
local res_key = KEYS[1]
local usage_key = KEYS[2]
local budget_key = KEYS[3]

local actual_req = tonumber(ARGV[1])
local actual_input = tonumber(ARGV[2])
local actual_output = tonumber(ARGV[3])
local actual_total = tonumber(ARGV[4])
local actual_cost = tonumber(ARGV[5])
local now = ARGV[6]
local ttl = tonumber(ARGV[7])

local status = redis.call("HGET", res_key, "status") or "not_found"
if status == "settled" then
    return "already_settled"
end
if status == "released" then
    return "already_released"
end
if status == "expired" then
    return "already_expired"
end
if status == "not_found" then
    return "not_found"
end

-- status == "pending": settle atomically
local est_req = tonumber(redis.call("HGET", res_key, "request_count") or "0")
local est_input = tonumber(redis.call("HGET", res_key, "input_tokens") or "0")
local est_output = tonumber(redis.call("HGET", res_key, "output_tokens") or "0")
local est_total = tonumber(redis.call("HGET", res_key, "total_tokens") or "0")
local est_cost = tonumber(redis.call("HGET", res_key, "estimated_cost") or "0")

-- Release reserved capacity
redis.call("HINCRBY", usage_key, "reserved_requests", -est_req)
redis.call("HINCRBY", usage_key, "reserved_input_tokens", -est_input)
redis.call("HINCRBY", usage_key, "reserved_output_tokens", -est_output)
redis.call("HINCRBY", usage_key, "reserved_total_tokens", -est_total)
redis.call("HINCRBYFLOAT", usage_key, "reserved_cost", -est_cost)

-- Record actual usage
redis.call("HINCRBY", usage_key, "request_count", actual_req)
redis.call("HINCRBY", usage_key, "input_tokens", actual_input)
redis.call("HINCRBY", usage_key, "output_tokens", actual_output)
redis.call("HINCRBY", usage_key, "total_tokens", actual_total)
redis.call("HINCRBYFLOAT", usage_key, "estimated_cost", actual_cost)
redis.call("HSET", usage_key, "updated_at", now)
redis.call("EXPIRE", usage_key, ttl)

local budget_exists = redis.call("EXISTS", budget_key)
if budget_exists == 1 and est_cost > 0 then
    redis.call("HINCRBYFLOAT", budget_key, "reserved_daily_cost", -est_cost)
    redis.call("HINCRBYFLOAT", budget_key, "reserved_monthly_cost", -est_cost)
    redis.call("HINCRBYFLOAT", budget_key, "daily_spend", actual_cost)
    redis.call("HINCRBYFLOAT", budget_key, "monthly_spend", actual_cost)
    redis.call("HSET", budget_key, "updated_at", now)
    redis.call("EXPIRE", budget_key, ttl)
end

redis.call("HSET", res_key,
    "status", "settled",
    "actual_cost", tostring(actual_cost),
    "actual_input_tokens", tostring(actual_input),
    "actual_output_tokens", tostring(actual_output),
    "updated_at", now
)
redis.call("EXPIRE", res_key, ttl)

return "settled"
"""


_RELEASE_RESERVATION_LUA = """
local res_key = KEYS[1]
local usage_key = KEYS[2]
local budget_key = KEYS[3]

local now = ARGV[1]
local ttl = tonumber(ARGV[2])

local status = redis.call("HGET", res_key, "status") or "not_found"
if status == "released" then
    return "already_released"
end
if status == "settled" then
    return "already_settled"
end
if status == "not_found" then
    return "not_found"
end

-- status == "pending" or "expired": release and free capacity
local est_req = tonumber(redis.call("HGET", res_key, "request_count") or "0")
local est_input = tonumber(redis.call("HGET", res_key, "input_tokens") or "0")
local est_output = tonumber(redis.call("HGET", res_key, "output_tokens") or "0")
local est_total = tonumber(redis.call("HGET", res_key, "total_tokens") or "0")
local est_cost = tonumber(redis.call("HGET", res_key, "estimated_cost") or "0")

redis.call("HINCRBY", usage_key, "reserved_requests", -est_req)
redis.call("HINCRBY", usage_key, "reserved_input_tokens", -est_input)
redis.call("HINCRBY", usage_key, "reserved_output_tokens", -est_output)
redis.call("HINCRBY", usage_key, "reserved_total_tokens", -est_total)
redis.call("HINCRBYFLOAT", usage_key, "reserved_cost", -est_cost)
redis.call("HSET", usage_key, "updated_at", now)
redis.call("EXPIRE", usage_key, ttl)

local budget_exists = redis.call("EXISTS", budget_key)
if budget_exists == 1 and est_cost > 0 then
    redis.call("HINCRBYFLOAT", budget_key, "reserved_daily_cost", -est_cost)
    redis.call("HINCRBYFLOAT", budget_key, "reserved_monthly_cost", -est_cost)
    redis.call("HSET", budget_key, "updated_at", now)
    redis.call("EXPIRE", budget_key, ttl)
end

redis.call("HSET", res_key, "status", "released", "updated_at", now)
redis.call("EXPIRE", res_key, ttl)

return "released"
"""


_MARK_EXPIRED_LUA = """
local cutoff = ARGV[1]
local now = ARGV[2]
local ttl = tonumber(ARGV[3])
local expired_ttl = tonumber(ARGV[4])

local status = redis.call("HGET", KEYS[1], "status") or "not_found"
if status ~= "pending" then
    return status
end

local created_at = redis.call("HGET", KEYS[1], "created_at") or ""
if created_at < cutoff then
    redis.call("HSET", KEYS[1], "status", "expired", "expired_at", now, "updated_at", now)
    redis.call("EXPIRE", KEYS[1], expired_ttl)
    return "expired"
end
redis.call("EXPIRE", KEYS[1], ttl)
return "pending"
"""


def _parse_dt(raw: str | None) -> datetime:
    if raw:
        try:
            return datetime.fromisoformat(raw)
        except (ValueError, TypeError):
            pass
    return utc_now()


class _AsyncRedis(Protocol):
    """Protocol declaring the async Redis operations used by this registry.

    The redis-py stubs annotate async methods as ``Awaitable[X] | X`` to
    accommodate the shared sync/async client surface.  This protocol narrows
    those annotations to fully-async signatures so MyPy can verify call sites
    without per-line ``# type: ignore`` suppressions.
    """

    async def hgetall(self, name: str) -> dict[str, str]: ...
    async def hset(self, name: str, mapping: dict[str, str]) -> int: ...
    async def expire(self, name: str, time: int) -> bool: ...
    async def delete(self, *keys: str) -> int: ...
    async def eval(
        self,
        script: str,
        numkeys: int,
        *keys_and_args: object,
    ) -> Any: ...

    def scan_iter(
        self,
        match: str | None = None,
        type: str | None = None,  # noqa: A002
    ) -> AsyncIterator[str]: ...

    async def aclose(self) -> None: ...


class RedisProviderQuotaRegistry(ProviderQuotaRegistry):
    """Redis-backed provider quota and usage state store."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or getattr(settings, "redis_url", None)
        self._client: _AsyncRedis | None = None

    async def _get_client(self) -> _AsyncRedis:
        if self._client is None:
            url = self._redis_url or settings.redis_url
            pool = aioredis.ConnectionPool.from_url(
                url,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
            )
            self._client = cast(_AsyncRedis, aioredis.Redis(connection_pool=pool))
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            with contextlib.suppress(Exception):
                await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> RedisProviderQuotaRegistry:
        await self._get_client()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def get_provider_quota(self, provider_id: str) -> ProviderQuotaConfig | None:
        client = await self._get_client()
        key = _provider_quota_key(provider_id)
        try:
            raw = await client.hgetall(key)
            if not raw:
                return None
            limits_raw = raw.get("limits")
            if limits_raw:
                import json

                limits_data = json.loads(limits_raw)
                limits = [
                    QuotaLimit(
                        window=QuotaWindow(entry["window"]),
                        request_limit=entry.get("request_limit"),
                        token_limit=entry.get("token_limit"),
                        cost_limit=Decimal(str(entry["cost_limit"]))
                        if entry.get("cost_limit") is not None
                        else None,
                    )
                    for entry in limits_data
                ]
            else:
                limits = []
            return ProviderQuotaConfig(provider_id=provider_id, limits=limits)
        except RedisError as exc:
            logger.warning("Failed to get provider quota", provider_id=provider_id, error=str(exc))
            return None

    async def set_provider_quota(self, config: ProviderQuotaConfig) -> None:
        client = await self._get_client()
        key = _provider_quota_key(config.provider_id)
        limits_data = [
            {
                "window": limit.window.value,
                "request_limit": limit.request_limit,
                "token_limit": limit.token_limit,
                "cost_limit": str(limit.cost_limit) if limit.cost_limit is not None else None,
            }
            for limit in config.limits
        ]
        try:
            await client.hset(
                key,
                mapping={
                    "provider_id": config.provider_id,
                    "limits": json.dumps(limits_data),
                },
            )
            await client.expire(key, 2592000)
        except RedisError as exc:
            logger.warning(
                "Failed to set provider quota",
                provider_id=config.provider_id,
                error=str(exc),
            )

    async def get_usage(self, provider_id: str, window: QuotaWindow) -> list[ProviderUsage]:
        client = await self._get_client()
        key = _provider_usage_key(provider_id, window)
        try:
            raw = await client.hgetall(key)
            if not raw:
                return []
            return [
                ProviderUsage(
                    provider_id=provider_id,
                    request_count=int(raw.get("request_count", 0)),
                    input_tokens=int(raw.get("input_tokens", 0)),
                    output_tokens=int(raw.get("output_tokens", 0)),
                    total_tokens=int(raw.get("total_tokens", 0)),
                    estimated_cost=Decimal(raw.get("estimated_cost", "0")),
                    window=window,
                    recorded_at=utc_now(),
                )
            ]
        except RedisError as exc:
            logger.warning("Failed to get provider usage", provider_id=provider_id, error=str(exc))
            return []

    async def record_usage(self, usage: ProviderUsage) -> None:
        client = await self._get_client()
        key = _provider_usage_key(usage.provider_id, usage.window)
        now = utc_now().isoformat()
        try:
            raw = await client.eval(
                _RECORD_USAGE_LUA,
                1,
                key,
                now,
                str(usage.request_count),
                str(usage.input_tokens),
                str(usage.output_tokens),
                str(usage.total_tokens),
                str(usage.estimated_cost),
                str(_USAGE_TTL_SECONDS),
            )
            if not raw:
                return
            logger.debug(
                "Recorded provider usage",
                provider_id=usage.provider_id,
                window=usage.window.value,
                request_count=usage.request_count,
                total_tokens=usage.total_tokens,
                cost=usage.estimated_cost,
            )
        except RedisError as exc:
            logger.warning(
                "Failed to record provider usage",
                provider_id=usage.provider_id,
                error=str(exc),
            )

    async def check_quota_eligibility(
        self,
        provider_id: str,
        window: QuotaWindow,
        estimated_tokens: int = 0,
        estimated_cost: float = 0.0,
        limit: QuotaLimit | None = None,
    ) -> QuotaEligibility:
        quota: ProviderQuotaConfig | None = None
        if limit is None:
            quota = await self.get_provider_quota(provider_id)
            if quota is None or not quota.limits:
                return QuotaEligibility(eligible=True, reason="no_quota_configured")

            limit = quota.limit_for(window)
            if limit is None:
                return QuotaEligibility(eligible=True, reason="no_limit_for_window")

        client = await self._get_client()
        key = _provider_usage_key(provider_id, window)
        try:
            result = await client.eval(
                _CHECK_QUOTA_LUA,
                1,
                key,
                str(limit.request_limit or -1),
                str(limit.token_limit or -1),
                str(limit.cost_limit or -1),
                str(estimated_tokens),
                str(estimated_cost),
            )
        except RedisError as exc:
            logger.warning(
                "Failed to check quota eligibility",
                provider_id=provider_id,
                error=str(exc),
            )
            return QuotaEligibility(eligible=True, reason="quota_check_failed")

        if result == "eligible":
            return QuotaEligibility(eligible=True, reason="eligible", quota=quota, limit=limit)
        if result == "request_exhausted":
            return QuotaEligibility(
                eligible=False,
                reason="request_quota_exhausted",
                quota=quota,
                limit=limit,
            )
        if result == "token_exhausted":
            return QuotaEligibility(
                eligible=False,
                reason="token_quota_exhausted",
                quota=quota,
                limit=limit,
            )
        if result == "cost_exhausted":
            return QuotaEligibility(
                eligible=False,
                reason="cost_quota_exhausted",
                quota=quota,
                limit=limit,
            )
        return QuotaEligibility(eligible=True, reason="unknown_check_result")

    async def reserve_capacity(
        self,
        request: QuotaReservationRequest,
    ) -> QuotaReservationResult:
        client = await self._get_client()

        has_provider_limit = request.limit is not None and (
            request.limit.request_limit is not None
            or request.limit.token_limit is not None
            or request.limit.cost_limit is not None
        )
        has_budget = request.daily_budget > 0 or request.monthly_budget > 0
        if not has_provider_limit and not has_budget:
            return QuotaReservationResult(
                reserved=False,
                reservation_id=request.reservation_id,
                reason="no_limits_configured",
            )

        usage_key = _provider_usage_key(request.provider_id, request.window)
        budget_key = _global_budget_key()
        res_key = _reservation_key(request.reservation_id)

        req_limit_val = (
            str(request.limit.request_limit)
            if request.limit and request.limit.request_limit is not None
            else "-1"
        )
        token_limit_val = (
            str(request.limit.token_limit)
            if request.limit and request.limit.token_limit is not None
            else "-1"
        )
        cost_limit_val = (
            str(request.limit.cost_limit)
            if request.limit and request.limit.cost_limit is not None
            else "-1"
        )

        now = utc_now().isoformat()
        ttl = str(_RESERVATION_TTL_SECONDS)

        try:
            result = await client.eval(
                _RESERVE_CAPACITY_LUA,
                3,
                usage_key,
                budget_key,
                res_key,
                str(request.request_count),
                str(request.input_tokens),
                str(request.output_tokens),
                str(request.total_tokens),
                str(request.estimated_cost),
                req_limit_val,
                token_limit_val,
                cost_limit_val,
                str(request.daily_budget),
                str(request.monthly_budget),
                request.reservation_id,
                request.provider_id,
                request.window.value,
                now,
                ttl,
            )
        except RedisError as exc:
            logger.warning(
                "Failed to reserve quota capacity",
                provider_id=request.provider_id,
                reservation_id=request.reservation_id,
                error=str(exc),
            )
            return QuotaReservationResult(
                reserved=False,
                reservation_id=request.reservation_id,
                reason="reserve_failed",
                budget_exceeded=False,
            )

        reason = str(result) if result else "unknown"
        if reason == "reserved":
            return QuotaReservationResult(
                reserved=True,
                reservation_id=request.reservation_id,
                reason="reserved",
            )
        if reason == "already_reserved":
            return QuotaReservationResult(
                reserved=True,
                reservation_id=request.reservation_id,
                reason="already_reserved",
            )
        budget_exhausted = reason in (
            "daily_budget_exhausted",
            "monthly_budget_exhausted",
            "request_exhausted",
            "token_exhausted",
            "cost_exhausted",
        )
        return QuotaReservationResult(
            reserved=False,
            reservation_id=request.reservation_id,
            reason=reason,
            budget_exceeded=budget_exhausted,
        )

    async def settle_reservation(
        self,
        reservation_id: str,
        actual_usage: ProviderUsage,
        actual_cost: float | None = None,
    ) -> SettlementResult:
        client = await self._get_client()
        res_key = _reservation_key(reservation_id)
        usage_key = _provider_usage_key(actual_usage.provider_id, actual_usage.window)
        budget_key = _global_budget_key()

        cost_value = actual_cost if actual_cost is not None else float(actual_usage.estimated_cost)
        now = utc_now().isoformat()
        ttl = str(_RESERVATION_TTL_SECONDS)

        try:
            result = await client.eval(
                _SETTLE_RESERVATION_LUA,
                3,
                res_key,
                usage_key,
                budget_key,
                str(actual_usage.request_count),
                str(actual_usage.input_tokens),
                str(actual_usage.output_tokens),
                str(actual_usage.total_tokens),
                str(Decimal(str(cost_value))),
                now,
                ttl,
            )
        except RedisError as exc:
            logger.warning(
                "Failed to settle reservation",
                reservation_id=reservation_id,
                error=str(exc),
            )
            return SettlementResult(
                settled=False,
                reservation_id=reservation_id,
                reason="settle_failed",
            )

        reason = str(result) if result else "unknown"
        if reason == "settled":
            return SettlementResult(
                settled=True,
                reservation_id=reservation_id,
                reason="settled",
                actual_cost=Decimal(str(cost_value)),
            )
        if reason in ("already_settled", "already_released"):
            return SettlementResult(
                settled=True,
                reservation_id=reservation_id,
                reason=reason,
                actual_cost=Decimal(str(cost_value)),
            )
        return SettlementResult(
            settled=False,
            reservation_id=reservation_id,
            reason=reason,
        )

    async def release_reservation(self, reservation_id: str) -> ReleaseResult:
        client = await self._get_client()
        res_key = _reservation_key(reservation_id)

        try:
            meta = await client.hgetall(res_key)
        except RedisError as exc:
            logger.warning(
                "Failed to load reservation for release",
                reservation_id=reservation_id,
                error=str(exc),
            )
            return ReleaseResult(
                released=False,
                reservation_id=reservation_id,
                reason="release_failed",
            )

        if not meta:
            return ReleaseResult(
                released=True,
                reservation_id=reservation_id,
                reason="not_found",
            )

        provider_id = meta.get("provider_id", "")
        window_str = meta.get("window", "day")
        try:
            window = QuotaWindow(window_str) if window_str else QuotaWindow.DAY
        except ValueError:
            window = QuotaWindow.DAY

        usage_key = _provider_usage_key(provider_id, window)
        budget_key = _global_budget_key()
        now = utc_now().isoformat()
        ttl = str(_RESERVATION_TTL_SECONDS)

        try:
            result = await client.eval(
                _RELEASE_RESERVATION_LUA,
                3,
                res_key,
                usage_key,
                budget_key,
                now,
                ttl,
            )
        except RedisError as exc:
            logger.warning(
                "Failed to release reservation",
                reservation_id=reservation_id,
                error=str(exc),
            )
            return ReleaseResult(
                released=False,
                reservation_id=reservation_id,
                reason="release_failed",
            )

        reason = str(result) if result else "unknown"
        if reason in ("released", "already_released", "already_settled", "not_found"):
            return ReleaseResult(
                released=True,
                reservation_id=reservation_id,
                reason=reason,
            )
        return ReleaseResult(
            released=False,
            reservation_id=reservation_id,
            reason=reason,
        )

    async def get_reservation(self, reservation_id: str) -> ReservationState | None:
        client = await self._get_client()
        key = _reservation_key(reservation_id)
        try:
            raw = await client.hgetall(key)
        except RedisError as exc:
            logger.warning(
                "Failed to get reservation", reservation_id=reservation_id, error=str(exc)
            )
            return None
        if not raw:
            return None
        try:
            window = QuotaWindow(raw.get("window", "day"))
        except ValueError:
            window = QuotaWindow.DAY
        try:
            status = ReservationStatus(raw.get("status", "pending"))
        except ValueError:
            status = ReservationStatus.PENDING
        return ReservationState(
            reservation_id=raw.get("reservation_id", reservation_id),
            provider_id=raw.get("provider_id", ""),
            window=window,
            status=status,
            request_count=int(raw.get("request_count", "0")),
            input_tokens=int(raw.get("input_tokens", "0")),
            output_tokens=int(raw.get("output_tokens", "0")),
            total_tokens=int(raw.get("total_tokens", "0")),
            estimated_cost=Decimal(raw.get("estimated_cost", "0")),
            actual_cost=Decimal(raw["actual_cost"]) if raw.get("actual_cost") else None,
            created_at=_parse_dt(raw.get("created_at")),
            updated_at=_parse_dt(raw.get("updated_at")),
            expired_at=_parse_dt(raw.get("expired_at")) if raw.get("expired_at") else None,
        )

    async def list_outstanding_reservations(self) -> list[ReservationState]:
        client = await self._get_client()
        reservations: list[ReservationState] = []
        try:
            async for key in client.scan_iter(match=_RESERVATION_PATTERN):
                raw = await client.hgetall(key)
                if not raw:
                    continue
                try:
                    window = QuotaWindow(raw.get("window", "day"))
                except ValueError:
                    window = QuotaWindow.DAY
                try:
                    status = ReservationStatus(raw.get("status", "pending"))
                except ValueError:
                    status = ReservationStatus.PENDING
                if status not in (ReservationStatus.PENDING, ReservationStatus.EXPIRED):
                    continue
                reservations.append(
                    ReservationState(
                        reservation_id=raw.get("reservation_id", ""),
                        provider_id=raw.get("provider_id", ""),
                        window=window,
                        status=status,
                        request_count=int(raw.get("request_count", "0")),
                        input_tokens=int(raw.get("input_tokens", "0")),
                        output_tokens=int(raw.get("output_tokens", "0")),
                        total_tokens=int(raw.get("total_tokens", "0")),
                        estimated_cost=Decimal(raw.get("estimated_cost", "0")),
                        created_at=_parse_dt(raw.get("created_at")),
                        updated_at=_parse_dt(raw.get("updated_at")),
                        expired_at=_parse_dt(raw.get("expired_at"))
                        if raw.get("expired_at")
                        else None,
                    )
                )
        except RedisError as exc:
            logger.warning("Failed to list outstanding reservations", error=str(exc))
        return reservations

    async def expire_reservations(self, max_age_seconds: int = 86400) -> int:
        client = await self._get_client()
        now = utc_now()
        cutoff = (now - timedelta(seconds=max_age_seconds)).isoformat()
        now_iso = now.isoformat()
        ttl = str(_RESERVATION_TTL_SECONDS)
        expired_ttl = str(_RESERVATION_EXPIRED_TTL_SECONDS)
        count = 0
        try:
            async for key in client.scan_iter(match=_RESERVATION_PATTERN):
                result = await client.eval(
                    _MARK_EXPIRED_LUA,
                    1,
                    key,
                    cutoff,
                    now_iso,
                    ttl,
                    expired_ttl,
                )
                if str(result) == "expired":
                    count += 1
        except RedisError as exc:
            logger.warning("Failed to expire reservations", error=str(exc))
        return count

    async def reconcile_reservations(
        self,
        max_age_seconds: int = 86400,
        batch_limit: int | None = None,
    ) -> int:
        """Mark old reservations as expired and release their capacity.

        This is the recovery entry-point: it first transitions stale pending
        reservations to the ``expired`` state (recording ``expired_at``), then
        releases each expired reservation so the reserved capacity — both
        provider-window counters and global budget — is returned to the
        available pool.

        When *batch_limit* is provided, at most that many reservations are
        released per call so a large backlog cannot monopolise a single worker
        cycle.  Unprocessed reservations remain in the ``expired`` state and
        will be picked up by the next reconciliation cycle.

        Returns the number of reservations that were reconciled
        (expired-and-released) in this batch.  Reservations that were already
        settled or released are skipped.
        """
        expired_count = await self.expire_reservations(max_age_seconds)
        if expired_count == 0:
            return 0

        outstanding = await self.list_outstanding_reservations()
        reconciled = 0
        for state in outstanding:
            if state.status != ReservationStatus.EXPIRED:
                continue
            if batch_limit is not None and reconciled >= batch_limit:
                break
            try:
                result = await self.release_reservation(state.reservation_id)
            except Exception as exc:
                logger.warning(
                    "Failed to release expired reservation during reconciliation",
                    reservation_id=state.reservation_id,
                    error=str(exc),
                )
                continue
            if result.released:
                reconciled += 1
        return reconciled

    async def get_global_budget(self) -> GlobalBudgetState:
        client = await self._get_client()
        key = _global_budget_key()
        try:
            raw = await client.hgetall(key)
            if not raw:
                return GlobalBudgetState()
            return GlobalBudgetState(
                daily_budget=Decimal(raw.get("daily_budget", "0")),
                monthly_budget=Decimal(raw.get("monthly_budget", "0")),
                daily_spend=Decimal(raw.get("daily_spend", "0")),
                monthly_spend=Decimal(raw.get("monthly_spend", "0")),
                reserved_daily_cost=Decimal(raw.get("reserved_daily_cost", "0")),
                reserved_monthly_cost=Decimal(raw.get("reserved_monthly_cost", "0")),
                updated_at=datetime.fromisoformat(raw.get("updated_at", ""))
                if raw.get("updated_at")
                else utc_now(),
            )
        except RedisError as exc:
            logger.warning("Failed to get global budget", error=str(exc))
            return GlobalBudgetState()

    async def update_global_budget(self, spend: float) -> GlobalBudgetState:
        client = await self._get_client()
        key = _global_budget_key()
        now = utc_now().isoformat()
        try:
            raw = await client.hgetall(key)
            daily_budget = Decimal(raw.get("daily_budget", "0")) if raw else Decimal("0")
            monthly_budget = Decimal(raw.get("monthly_budget", "0")) if raw else Decimal("0")
            daily_spend = Decimal(raw.get("daily_spend", "0")) if raw else Decimal("0")
            monthly_spend = Decimal(raw.get("monthly_spend", "0")) if raw else Decimal("0")

            daily_spend += Decimal(str(spend))
            monthly_spend += Decimal(str(spend))

            await client.hset(
                key,
                mapping={
                    "daily_budget": str(daily_budget),
                    "monthly_budget": str(monthly_budget),
                    "daily_spend": str(daily_spend),
                    "monthly_spend": str(monthly_spend),
                    "updated_at": now,
                },
            )
            await client.expire(key, 2592000)
            return GlobalBudgetState(
                daily_budget=daily_budget,
                monthly_budget=monthly_budget,
                daily_spend=daily_spend,
                monthly_spend=monthly_spend,
                updated_at=utc_now(),
            )
        except RedisError as exc:
            logger.warning("Failed to update global budget", error=str(exc))
            return GlobalBudgetState()

    async def reset_provider_quota(self, provider_id: str) -> None:
        client = await self._get_client()
        try:
            keys = []
            async for key in client.scan_iter(match=f"{_NAMESPACE}:{provider_id}:usage:*"):
                keys.append(key)
            for key in keys:
                await client.delete(key)
        except RedisError as exc:
            logger.warning(
                "Failed to reset provider quota",
                provider_id=provider_id,
                error=str(exc),
            )

    async def get_all_quota_states(self) -> dict[str, ProviderQuotaConfig]:
        client = await self._get_client()
        result: dict[str, ProviderQuotaConfig] = {}
        try:
            async for key in client.scan_iter(match=f"{_NAMESPACE}:*"):
                raw = await client.hgetall(key)
                if not raw:
                    continue
                provider_id = raw.get("provider_id", "")
                if not provider_id or key.count(":") > 2:
                    continue
                limits_raw = raw.get("limits")
                if limits_raw:
                    limits_data = json.loads(limits_raw)
                    limits = [
                        QuotaLimit(
                            window=QuotaWindow(entry["window"]),
                            request_limit=entry.get("request_limit"),
                            token_limit=entry.get("token_limit"),
                            cost_limit=Decimal(str(entry["cost_limit"]))
                            if entry.get("cost_limit") is not None
                            else None,
                        )
                        for entry in limits_data
                    ]
                else:
                    limits = []
                result[provider_id] = ProviderQuotaConfig(provider_id=provider_id, limits=limits)
        except RedisError as exc:
            logger.warning("Failed to get all quota states", error=str(exc))
        return result


__all__ = ["RedisProviderQuotaRegistry"]
