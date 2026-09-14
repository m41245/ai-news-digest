from __future__ import annotations

import contextlib
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from ai_news_digest.application.ai.provider_health import (
    CircuitBreakerPolicy,
    CircuitState,
    FailureCategory,
    ProviderHealthState,
    counts_toward_circuit,
    utc_now,
)
from ai_news_digest.application.ai.provider_health_registry import (
    ProviderHealthRegistry,
)
from ai_news_digest.core.config import settings
from ai_news_digest.core.logging import get_logger

logger = get_logger(__name__)

_NAMESPACE = "ai:provider-health"
_PROBE_LEASE_NAMESPACE = "ai:provider-health:probe-lease"
_PROBE_LEASE_TTL_SECONDS = 5


def _provider_key(provider_id: str) -> str:
    return f"{_NAMESPACE}:{provider_id}"


def _probe_lease_key(provider_id: str) -> str:
    return f"{_PROBE_LEASE_NAMESPACE}:{provider_id}"


_RECORD_FAILURE_LUA = """
local key = KEYS[1]
local now = ARGV[1]
local category = ARGV[2]
local threshold = tonumber(ARGV[3])
local cooldown_seconds = tonumber(ARGV[4])
local counts = ARGV[5]

local state = redis.call("HGET", key, "state") or "closed"
local consecutive_failures = tonumber(redis.call("HGET", key, "consecutive_failures") or "0")

if counts == "false" then
    return redis.call("HGETALL", key)
end

consecutive_failures = consecutive_failures + 1

if state == "half_open" then
    redis.call("HSET", key, "state", "open",
        "consecutive_failures", consecutive_failures,
        "last_failure_at", now, "opened_at", now)
    local cooldown_until = now + cooldown_seconds
    redis.call("HSET", key, "cooldown_until", tostring(cooldown_until))
    redis.call("EXPIRE", key, math.ceil(cooldown_seconds + 60))
    return redis.call("HGETALL", key)
end

if consecutive_failures >= threshold then
    redis.call("HSET", key, "state", "open",
        "consecutive_failures", consecutive_failures,
        "last_failure_at", now, "opened_at", now)
    local cooldown_until = now + cooldown_seconds
    redis.call("HSET", key, "cooldown_until", tostring(cooldown_until))
    redis.call("EXPIRE", key, math.ceil(cooldown_seconds + 60))
else
    redis.call("HSET", key, "state", "closed",
        "consecutive_failures", consecutive_failures,
        "last_failure_at", now)
    redis.call("EXPIRE", key, 3600)
end

return redis.call("HGETALL", key)
"""

_RECORD_SUCCESS_LUA = """
local key = KEYS[1]
local now = ARGV[1]
local success_threshold = tonumber(ARGV[2])

local state = redis.call("HGET", key, "state") or "closed"
local consecutive_successes = tonumber(redis.call("HGET", key, "consecutive_successes") or "0")
local consecutive_failures = tonumber(redis.call("HGET", key, "consecutive_failures") or "0")

consecutive_successes = consecutive_successes + 1

if state == "half_open" and consecutive_successes >= success_threshold then
    redis.call("HSET", key, "state", "closed",
        "consecutive_successes", 0, "consecutive_failures", 0,
        "last_success_at", now, "cooldown_until", "", "opened_at", "")
    redis.call("EXPIRE", key, 3600)
else
    redis.call("HSET", key, "state", "closed",
        "consecutive_successes", consecutive_successes,
        "consecutive_failures", 0, "last_success_at", now)
    redis.call("EXPIRE", key, 3600)
end

return redis.call("HGETALL", key)
"""

_TRY_ACQUIRE_PROBE_LEASE_LUA = """
local key = KEYS[1]
local lease_key = KEYS[2]
local now = ARGV[1]
local lease_ttl = tonumber(ARGV[2])

local state = redis.call("HGET", key, "state") or "closed"
local cooldown_until = redis.call("HGET", key, "cooldown_until")

if state ~= "open" then
    return "0"
end

if cooldown_until and tonumber(cooldown_until) > tonumber(now) then
    return "0"
end

local lease_acquired = redis.call("SET", lease_key, now, "NX", "EX", lease_ttl)
if not lease_acquired then
    return "0"
end

redis.call("HSET", key, "state", "half_open", "next_probe_at", now)
redis.call("EXPIRE", key, 3600)
return "1"
"""


class RedisProviderHealthRegistry(ProviderHealthRegistry):
    """Redis-backed provider health and circuit breaker state store."""

    def __init__(
        self,
        redis_url: str | None = None,
        policy: CircuitBreakerPolicy | None = None,
    ) -> None:
        self._redis_url = redis_url or getattr(settings, "redis_url", None)
        self._policy = policy or CircuitBreakerPolicy()
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

    async def __aenter__(self) -> RedisProviderHealthRegistry:
        await self._get_client()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    def _decode_state(self, raw: dict[str, str]) -> ProviderHealthState:
        def _parse_ts(value: str | None) -> datetime | None:
            if not value:
                return None
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None

        state_str = raw.get("state", "closed")
        try:
            state = CircuitState(state_str)
        except ValueError:
            state = CircuitState.CLOSED

        return ProviderHealthState(
            provider_id=raw.get("provider_id", ""),
            state=state,
            consecutive_failures=int(raw.get("consecutive_failures", 0)),
            consecutive_successes=int(raw.get("consecutive_successes", 0)),
            last_failure_at=_parse_ts(raw.get("last_failure_at")),
            last_success_at=_parse_ts(raw.get("last_success_at")),
            opened_at=_parse_ts(raw.get("opened_at")),
            cooldown_until=_parse_ts(raw.get("cooldown_until")),
            next_probe_at=_parse_ts(raw.get("next_probe_at")),
            metadata={},
        )

    async def get_state(self, provider_id: str) -> ProviderHealthState:
        client = await self._get_client()
        key = _provider_key(provider_id)
        try:
            raw = await client.hgetall(key)  # type: ignore[misc]
            if not raw:
                return ProviderHealthState(provider_id=provider_id)
            raw["provider_id"] = provider_id
            return self._decode_state(raw)
        except RedisError as exc:
            logger.warning(
                "Failed to get provider health state",
                provider_id=provider_id,
                error=str(exc),
            )
            return ProviderHealthState(provider_id=provider_id)

    async def record_success(self, provider_id: str) -> ProviderHealthState:
        client = await self._get_client()
        key = _provider_key(provider_id)
        now = utc_now().isoformat()
        try:
            raw = await client.eval(  # type: ignore[misc]
                _RECORD_SUCCESS_LUA,
                1,
                key,
                now,
                str(self._policy.success_threshold_to_close),
            )
            if not raw:
                return ProviderHealthState(
                    provider_id=provider_id, state=CircuitState.CLOSED
                )
            raw = dict(zip(raw[::2], raw[1::2], strict=True))
            raw["provider_id"] = provider_id
            state = self._decode_state(raw)
            if state.state == CircuitState.CLOSED and state.consecutive_failures == 0:
                logger.info(
                    "Provider circuit closed",
                    provider_id=provider_id,
                    consecutive_successes=state.consecutive_successes,
                )
            return state
        except RedisError as exc:
            logger.warning(
                "Failed to record provider success",
                provider_id=provider_id,
                error=str(exc),
            )
            return ProviderHealthState(provider_id=provider_id)

    async def record_failure(
        self,
        provider_id: str,
        category: str | FailureCategory,
    ) -> ProviderHealthState:
        cat_str = category.value if isinstance(category, FailureCategory) else str(category)
        cat_enum = FailureCategory(cat_str)
        client = await self._get_client()
        key = _provider_key(provider_id)
        now = utc_now().isoformat()
        counts = counts_toward_circuit(cat_enum)
        try:
            raw = await client.eval(  # type: ignore[misc]
                _RECORD_FAILURE_LUA,
                1,
                key,
                now,
                cat_str,
                str(self._policy.failure_threshold),
                str(self._policy.cooldown_seconds),
                str(counts).lower(),
            )
            if not raw:
                return ProviderHealthState(provider_id=provider_id)
            raw = dict(zip(raw[::2], raw[1::2], strict=True))
            raw["provider_id"] = provider_id
            state = self._decode_state(raw)
            if state.state == CircuitState.OPEN:
                logger.warning(
                    "Provider circuit opened",
                    provider_id=provider_id,
                    failure_category=cat_str,
                    consecutive_failures=state.consecutive_failures,
                    cooldown_until=(
                        str(state.cooldown_until) if state.cooldown_until else None
                    ),
                )
            else:
                logger.info(
                    "Provider failure recorded",
                    provider_id=provider_id,
                    failure_category=cat_str,
                    consecutive_failures=state.consecutive_failures,
                    state=state.state.value,
                )
            return state
        except RedisError as exc:
            logger.warning(
                "Failed to record provider failure",
                provider_id=provider_id,
                error=str(exc),
            )
            return ProviderHealthState(provider_id=provider_id)

    async def is_eligible(self, provider_id: str) -> bool:
        state = await self.get_state(provider_id)
        if state.state == CircuitState.CLOSED:
            return True
        if state.state == CircuitState.HALF_OPEN:
            return False
        if state.state == CircuitState.OPEN:
            now = utc_now()
            if state.cooldown_until is not None and now >= state.cooldown_until:
                return False
            return False
        raise AssertionError(f"Unknown circuit state: {state.state}")

    async def try_acquire_probe_lease(self, provider_id: str) -> bool:
        client = await self._get_client()
        key = _provider_key(provider_id)
        lease_key = _probe_lease_key(provider_id)
        now = utc_now().timestamp()
        try:
            result = await client.eval(  # type: ignore[misc]
                _TRY_ACQUIRE_PROBE_LEASE_LUA,
                2,
                key,
                lease_key,
                str(now),
                str(_PROBE_LEASE_TTL_SECONDS),
            )
            acquired = bool(result) and str(result) == "1"
            if acquired:
                logger.info("Acquired half-open probe lease", provider_id=provider_id)
            return acquired
        except RedisError as exc:
            logger.warning(
                "Failed to acquire probe lease",
                provider_id=provider_id,
                error=str(exc),
            )
            return False

    async def release_probe_lease(self, provider_id: str) -> None:
        client = await self._get_client()
        lease_key = _probe_lease_key(provider_id)
        try:
            await client.delete(lease_key)
        except RedisError as exc:
            logger.warning(
                "Failed to release probe lease",
                provider_id=provider_id,
                error=str(exc),
            )

    async def reset(self, provider_id: str) -> ProviderHealthState:
        client = await self._get_client()
        key = _provider_key(provider_id)
        now = utc_now().isoformat()
        try:
            await client.hset(  # type: ignore[misc]
                key,
                mapping={
                    "provider_id": provider_id,
                    "state": CircuitState.CLOSED.value,
                    "consecutive_failures": "0",
                    "consecutive_successes": "0",
                    "last_failure_at": "",
                    "last_success_at": now,
                    "opened_at": "",
                    "cooldown_until": "",
                    "next_probe_at": "",
                },
            )
            await client.expire(key, 3600)
            logger.info("Provider circuit reset", provider_id=provider_id)
            return ProviderHealthState(
                provider_id=provider_id, state=CircuitState.CLOSED
            )
        except RedisError as exc:
            logger.warning(
                "Failed to reset provider health",
                provider_id=provider_id,
                error=str(exc),
            )
            return ProviderHealthState(provider_id=provider_id)

    async def get_all_states(self) -> dict[str, ProviderHealthState]:
        client = await self._get_client()
        try:
            keys = []
            async for key in client.scan_iter(match=f"{_NAMESPACE}:*"):
                keys.append(key)
            result = {}
            for key in keys:
                raw = await client.hgetall(key)  # type: ignore[misc]
                if not raw:
                    continue
                provider_id = raw.get("provider_id") or key.split(":")[-1]
                raw["provider_id"] = provider_id
                result[provider_id] = self._decode_state(raw)
            return result
        except RedisError as exc:
            logger.warning(
                "Failed to get all provider health states", error=str(exc)
            )
            return {}


__all__ = ["RedisProviderHealthRegistry"]
