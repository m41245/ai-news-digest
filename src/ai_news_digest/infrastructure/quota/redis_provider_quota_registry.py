from __future__ import annotations

import contextlib
from datetime import datetime
from decimal import Decimal
from typing import Any

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
    QuotaWindow,
)
from ai_news_digest.core.config import settings
from ai_news_digest.core.logging import get_logger

logger = get_logger(__name__)

_NAMESPACE = "ai:provider-quota"
_BUDGET_NAMESPACE = "ai:budget"
_USAGE_TTL_SECONDS = 2592000


def _provider_quota_key(provider_id: str) -> str:
    return f"{_NAMESPACE}:{provider_id}"


def _provider_usage_key(provider_id: str, window: QuotaWindow) -> str:
    return f"{_NAMESPACE}:{provider_id}:usage:{window.value}"


def _global_budget_key() -> str:
    return f"{_BUDGET_NAMESPACE}:global"


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

if req_limit ~= nil and req_limit >= 0 and current_req >= req_limit then
    return "request_exhausted"
end
if token_limit ~= nil and token_limit >= 0 and (current_tokens + est_tokens) > token_limit then
    return "token_exhausted"
end
if cost_limit ~= nil and cost_limit >= 0 and (current_cost + est_cost) > cost_limit then
    return "cost_exhausted"
end
return "eligible"
"""


class RedisProviderQuotaRegistry(ProviderQuotaRegistry):
    """Redis-backed provider quota and usage state store."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = redis_url or getattr(settings, "redis_url", None)
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            url = self._redis_url or settings.redis_url
            pool = aioredis.ConnectionPool.from_url(
                url,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
            )
            self._client = aioredis.Redis(connection_pool=pool)
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
        import json
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
    ) -> QuotaEligibility:
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
            import json
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
