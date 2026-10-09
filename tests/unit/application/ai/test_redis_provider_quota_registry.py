"""
Unit tests for M79 Redis provider quota registry.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.exceptions import RedisError

from ai_news_digest.application.ai.quota import (
    ProviderQuotaConfig,
    ProviderUsage,
    QuotaLimit,
    QuotaReservationRequest,
    QuotaWindow,
    ReservationStatus,
)
from ai_news_digest.infrastructure.quota.redis_provider_quota_registry import (
    _MARK_EXPIRED_LUA,
    _RELEASE_RESERVATION_LUA,
    _RESERVATION_EXPIRED_TTL_SECONDS,
    _RESERVATION_TTL_SECONDS,
    RedisProviderQuotaRegistry,
    _provider_quota_key,
    _provider_usage_key,
    _reservation_key,
    _window_id,
)


@pytest.fixture
def quota_registry() -> RedisProviderQuotaRegistry:
    return RedisProviderQuotaRegistry(redis_url="redis://localhost:6379/0")


def test_window_id_minute() -> None:
    dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
    assert _window_id(QuotaWindow.MINUTE, dt) == "202401151030"


def test_window_id_hour() -> None:
    dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
    assert _window_id(QuotaWindow.HOUR, dt) == "2024011510"


def test_window_id_day() -> None:
    dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
    assert _window_id(QuotaWindow.DAY, dt) == "20240115"


def test_window_id_month() -> None:
    dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
    assert _window_id(QuotaWindow.MONTH, dt) == "202401"


def test_provider_quota_key() -> None:
    assert _provider_quota_key("openai") == "ai:provider-quota:openai"


def test_provider_usage_key() -> None:
    assert _provider_usage_key("openai", QuotaWindow.DAY) == "ai:provider-quota:openai:usage:day"


@pytest.mark.asyncio
async def test_get_provider_quota_returns_none_when_absent(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {}
    quota_registry._client = mock_client

    result = await quota_registry.get_provider_quota("openai")
    assert result is None


@pytest.mark.asyncio
async def test_set_and_get_provider_quota(quota_registry: RedisProviderQuotaRegistry) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {}
    quota_registry._client = mock_client

    config = ProviderQuotaConfig(
        provider_id="openai",
        limits=[
            QuotaLimit(window=QuotaWindow.DAY, request_limit=100, token_limit=10000),
        ],
    )
    await quota_registry.set_provider_quota(config)

    mock_client.hset.assert_called_once()
    mock_client.expire.assert_called_once()

    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "limits": json.dumps(
            [{"window": "day", "request_limit": 100, "token_limit": 10000, "cost_limit": None}]
        ),
    }
    result = await quota_registry.get_provider_quota("openai")
    assert result is not None
    assert result.provider_id == "openai"
    assert len(result.limits) == 1
    assert result.limits[0].request_limit == 100


@pytest.mark.asyncio
async def test_record_usage_success(quota_registry: RedisProviderQuotaRegistry) -> None:
    mock_client = AsyncMock()
    mock_client.eval.return_value = []
    quota_registry._client = mock_client

    usage = ProviderUsage(
        provider_id="openai",
        request_count=1,
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        estimated_cost=Decimal("0.01"),
        window=QuotaWindow.DAY,
    )
    await quota_registry.record_usage(usage)

    mock_client.eval.assert_called_once()


@pytest.mark.asyncio
async def test_check_quota_eligible_when_no_limits(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {}
    quota_registry._client = mock_client

    result = await quota_registry.check_quota_eligibility("openai", QuotaWindow.DAY)
    assert result.eligible is True
    assert result.reason == "no_quota_configured"


@pytest.mark.asyncio
async def test_check_quota_eligible_when_under_limit(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {}
    mock_client.eval.return_value = "eligible"
    quota_registry._client = mock_client

    config = ProviderQuotaConfig(
        provider_id="openai",
        limits=[
            QuotaLimit(
                window=QuotaWindow.DAY,
                request_limit=100,
                token_limit=10000,
                cost_limit=Decimal("5.0"),
            )
        ],
    )
    await quota_registry.set_provider_quota(config)

    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "limits": json.dumps(
            [{"window": "day", "request_limit": 100, "token_limit": 10000, "cost_limit": "5.0"}]
        ),
    }
    result = await quota_registry.check_quota_eligibility(
        "openai", QuotaWindow.DAY, estimated_tokens=100, estimated_cost=0.1
    )
    assert result.eligible is True
    assert result.reason == "eligible"


@pytest.mark.asyncio
async def test_check_quota_excluded_when_request_limit_exhausted(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "limits": json.dumps(
            [{"window": "day", "request_limit": 100, "token_limit": 10000, "cost_limit": "5.0"}]
        ),
    }
    mock_client.eval.return_value = "request_exhausted"
    quota_registry._client = mock_client

    result = await quota_registry.check_quota_eligibility(
        "openai", QuotaWindow.DAY, estimated_tokens=100, estimated_cost=0.1
    )
    assert result.eligible is False
    assert result.reason == "request_quota_exhausted"


@pytest.mark.asyncio
async def test_get_global_budget_defaults(quota_registry: RedisProviderQuotaRegistry) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {}
    quota_registry._client = mock_client

    result = await quota_registry.get_global_budget()
    assert result.daily_budget == Decimal("0")
    assert result.monthly_budget == Decimal("0")


@pytest.mark.asyncio
async def test_update_global_budget(quota_registry: RedisProviderQuotaRegistry) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "daily_budget": "10.0",
        "monthly_budget": "100.0",
        "daily_spend": "0.0",
        "monthly_spend": "0.0",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    quota_registry._client = mock_client

    result = await quota_registry.update_global_budget(1.5)
    assert result.daily_spend == Decimal("1.5")
    assert result.monthly_spend == Decimal("1.5")


@pytest.mark.asyncio
async def test_redis_error_handled_gracefully(quota_registry: RedisProviderQuotaRegistry) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.side_effect = RedisError("connection lost")
    quota_registry._client = mock_client

    result = await quota_registry.get_provider_quota("openai")
    assert result is None

    result = await quota_registry.check_quota_eligibility("openai", QuotaWindow.DAY)
    assert result.eligible is True
    assert result.reason == "no_quota_configured"


@pytest.mark.asyncio
async def test_check_quota_with_explicit_limit_skips_quota_read(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """An explicit limit avoids a redundant quota-config read from Redis."""
    mock_client = AsyncMock()
    mock_client.eval.return_value = "eligible"
    quota_registry._client = mock_client

    limit = QuotaLimit(
        window=QuotaWindow.DAY, request_limit=42, token_limit=420, cost_limit=Decimal("1.5")
    )
    result = await quota_registry.check_quota_eligibility(
        "openai", QuotaWindow.DAY, estimated_tokens=10, estimated_cost=0.1, limit=limit
    )

    assert result.eligible is True
    assert result.reason == "eligible"
    # No quota-config hash lookup should have happened for an explicit limit.
    assert mock_client.hgetall.call_count == 0
    args = mock_client.eval.call_args.args
    # eval(lua, numkeys=1, key, request_limit, token_limit, cost_limit, tokens, cost)
    assert args[3] == str(limit.request_limit)
    assert args[4] == str(limit.token_limit)
    assert args[5] == str(limit.cost_limit)


@pytest.mark.asyncio
async def test_check_quota_with_explicit_limit_reports_exhaustion(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.eval.return_value = "cost_exhausted"
    quota_registry._client = mock_client

    limit = QuotaLimit(window=QuotaWindow.DAY, cost_limit=Decimal("1.0"))
    result = await quota_registry.check_quota_eligibility(
        "openai", QuotaWindow.DAY, estimated_tokens=0, estimated_cost=0.5, limit=limit
    )

    assert result.eligible is False
    assert result.reason == "cost_quota_exhausted"
    assert result.limit is limit


@pytest.mark.asyncio
async def test_check_quota_with_explicit_limit_fails_open_on_redis_error(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.eval.side_effect = RedisError("connection lost")
    quota_registry._client = mock_client

    limit = QuotaLimit(window=QuotaWindow.DAY, request_limit=5)
    result = await quota_registry.check_quota_eligibility(
        "openai", QuotaWindow.DAY, estimated_tokens=1, estimated_cost=0.0, limit=limit
    )

    assert result.eligible is True
    assert result.reason == "quota_check_failed"


# ======================================================================
# Reservation lifecycle tests
# ======================================================================


def _make_reservation_request(
    reservation_id: str = "res-1",
    provider_id: str = "openai",
    request_count: int = 1,
    input_tokens: int = 100,
    output_tokens: int = 50,
    total_tokens: int = 150,
    estimated_cost: float = 0.003,
    req_limit: int = 1000,
    token_limit: int = 100000,
    cost_limit: float = 10.0,
    daily_budget: float = 50.0,
    monthly_budget: float = 500.0,
) -> QuotaReservationRequest:
    return QuotaReservationRequest(
        provider_id=provider_id,
        reservation_id=reservation_id,
        window=QuotaWindow.DAY,
        request_count=request_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost=Decimal(str(estimated_cost)),
        cost_known=True,
        limit=QuotaLimit(
            window=QuotaWindow.DAY,
            request_limit=req_limit,
            token_limit=token_limit,
            cost_limit=Decimal(str(cost_limit)),
        ),
        daily_budget=Decimal(str(daily_budget)),
        monthly_budget=Decimal(str(monthly_budget)),
    )


@pytest.fixture
def reservation_request() -> QuotaReservationRequest:
    return _make_reservation_request()


@pytest.mark.asyncio
async def test_reserve_capacity_success(
    quota_registry: RedisProviderQuotaRegistry,
    reservation_request: QuotaReservationRequest,
) -> None:
    mock_client = AsyncMock()
    mock_client.eval.return_value = "reserved"
    quota_registry._client = mock_client

    result = await quota_registry.reserve_capacity(reservation_request)
    assert result.reserved is True
    assert result.reason == "reserved"
    mock_client.eval.assert_called_once()


@pytest.mark.asyncio
async def test_reserve_capacity_rejects_request_limit_exceeded(
    quota_registry: RedisProviderQuotaRegistry,
    reservation_request: QuotaReservationRequest,
) -> None:
    mock_client = AsyncMock()
    mock_client.eval.return_value = "request_exhausted"
    quota_registry._client = mock_client

    result = await quota_registry.reserve_capacity(reservation_request)
    assert result.reserved is False
    assert result.reason == "request_exhausted"
    assert result.budget_exceeded is True


@pytest.mark.asyncio
async def test_reserve_capacity_rejects_token_limit_exceeded(
    quota_registry: RedisProviderQuotaRegistry,
    reservation_request: QuotaReservationRequest,
) -> None:
    mock_client = AsyncMock()
    mock_client.eval.return_value = "token_exhausted"
    quota_registry._client = mock_client

    result = await quota_registry.reserve_capacity(reservation_request)
    assert result.reserved is False
    assert result.reason == "token_exhausted"
    assert result.budget_exceeded is True


@pytest.mark.asyncio
async def test_reserve_capacity_rejects_provider_cost_limit_exceeded(
    quota_registry: RedisProviderQuotaRegistry,
    reservation_request: QuotaReservationRequest,
) -> None:
    mock_client = AsyncMock()
    mock_client.eval.return_value = "cost_exhausted"
    quota_registry._client = mock_client

    result = await quota_registry.reserve_capacity(reservation_request)
    assert result.reserved is False
    assert result.reason == "cost_exhausted"
    assert result.budget_exceeded is True


@pytest.mark.asyncio
async def test_reserve_capacity_rejects_daily_budget_exceeded(
    quota_registry: RedisProviderQuotaRegistry,
    reservation_request: QuotaReservationRequest,
) -> None:
    mock_client = AsyncMock()
    mock_client.eval.return_value = "daily_budget_exhausted"
    quota_registry._client = mock_client

    result = await quota_registry.reserve_capacity(reservation_request)
    assert result.reserved is False
    assert result.reason == "daily_budget_exhausted"
    assert result.budget_exceeded is True


@pytest.mark.asyncio
async def test_reserve_capacity_rejects_monthly_budget_exceeded(
    quota_registry: RedisProviderQuotaRegistry,
    reservation_request: QuotaReservationRequest,
) -> None:
    mock_client = AsyncMock()
    mock_client.eval.return_value = "monthly_budget_exhausted"
    quota_registry._client = mock_client

    result = await quota_registry.reserve_capacity(reservation_request)
    assert result.reserved is False
    assert result.reason == "monthly_budget_exhausted"
    assert result.budget_exceeded is True


@pytest.mark.asyncio
async def test_reserve_capacity_fails_closed_on_redis_error(
    quota_registry: RedisProviderQuotaRegistry,
    reservation_request: QuotaReservationRequest,
) -> None:
    mock_client = AsyncMock()
    mock_client.eval.side_effect = RedisError("connection lost")
    quota_registry._client = mock_client

    result = await quota_registry.reserve_capacity(reservation_request)
    assert result.reserved is False
    assert result.reason == "reserve_failed"


@pytest.mark.asyncio
async def test_reserve_capacity_already_reserved_is_idempotent(
    quota_registry: RedisProviderQuotaRegistry,
    reservation_request: QuotaReservationRequest,
) -> None:
    mock_client = AsyncMock()
    mock_client.eval.return_value = "already_reserved"
    quota_registry._client = mock_client

    result = await quota_registry.reserve_capacity(reservation_request)
    assert result.reserved is True
    assert result.reason == "already_reserved"


@pytest.mark.asyncio
async def test_settle_reservation_success(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.eval.return_value = "settled"
    quota_registry._client = mock_client

    usage = ProviderUsage(
        provider_id="openai",
        request_count=1,
        input_tokens=12,
        output_tokens=8,
        total_tokens=20,
        estimated_cost=Decimal("0.004"),
        usage_known=True,
        window=QuotaWindow.DAY,
    )
    result = await quota_registry.settle_reservation("res-1", usage, actual_cost=0.004)
    assert result.settled is True
    assert result.reason == "settled"


@pytest.mark.asyncio
async def test_settle_reservation_idempotent_on_duplicate(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.eval.return_value = "already_settled"
    quota_registry._client = mock_client

    usage = ProviderUsage(provider_id="openai", window=QuotaWindow.DAY)
    result = await quota_registry.settle_reservation("res-1", usage, actual_cost=0.004)
    assert result.settled is True
    assert result.reason == "already_settled"


@pytest.mark.asyncio
async def test_settle_reservation_does_not_release_settled(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """A duplicate settlement on an already-settled reservation must not
    double-count or refund."""
    mock_client = AsyncMock()
    mock_client.eval.return_value = "already_settled"
    quota_registry._client = mock_client

    usage = ProviderUsage(provider_id="openai", window=QuotaWindow.DAY)
    result = await quota_registry.settle_reservation("res-1", usage, actual_cost=0.004)
    assert result.settled is True


@pytest.mark.asyncio
async def test_release_reservation_success(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "window": "day",
    }
    mock_client.eval.return_value = "released"
    quota_registry._client = mock_client

    result = await quota_registry.release_reservation("res-1")
    assert result.released is True
    assert result.reason == "released"


@pytest.mark.asyncio
async def test_release_reservation_idempotent(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "window": "day",
    }
    mock_client.eval.side_effect = ["released", "already_released"]
    quota_registry._client = mock_client

    first = await quota_registry.release_reservation("res-1")
    second = await quota_registry.release_reservation("res-1")
    assert first.released is True
    assert second.released is True
    assert first.reason == "released"
    assert second.reason == "already_released"


@pytest.mark.asyncio
async def test_release_reservation_not_found_is_noop(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {}
    quota_registry._client = mock_client

    result = await quota_registry.release_reservation("res-missing")
    assert result.released is True
    assert result.reason == "not_found"


@pytest.mark.asyncio
async def test_release_after_settlement_cannot_refund(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """Releasing a settled reservation must not free capacity — it is a
    safe no-op returning already_settled."""
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "window": "day",
    }
    mock_client.eval.return_value = "already_settled"
    quota_registry._client = mock_client

    result = await quota_registry.release_reservation("res-1")
    assert result.released is True
    assert result.reason == "already_settled"


@pytest.mark.asyncio
async def test_get_reservation_returns_state(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "reservation_id": "res-1",
        "provider_id": "openai",
        "window": "day",
        "request_count": "1",
        "input_tokens": "100",
        "output_tokens": "50",
        "total_tokens": "150",
        "estimated_cost": "0.003",
        "status": "pending",
        "created_at": "2024-01-15T10:30:00+00:00",
        "updated_at": "2024-01-15T10:30:00+00:00",
    }
    quota_registry._client = mock_client

    state = await quota_registry.get_reservation("res-1")
    assert state is not None
    assert state.reservation_id == "res-1"
    assert state.provider_id == "openai"
    assert state.status == ReservationStatus.PENDING
    assert state.estimated_cost == Decimal("0.003")


@pytest.mark.asyncio
async def test_get_reservation_returns_none_when_absent(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {}
    quota_registry._client = mock_client

    state = await quota_registry.get_reservation("res-missing")
    assert state is None


@pytest.mark.asyncio
async def test_reserve_capacity_fails_closed_with_no_limits(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """If the reservation request has no limit and no budget, fail closed."""
    mock_client = AsyncMock()
    quota_registry._client = mock_client

    request_no_limit = QuotaReservationRequest(
        provider_id="openai",
        reservation_id="res-1",
        window=QuotaWindow.DAY,
        estimated_cost=Decimal("0.001"),
        limit=None,
        daily_budget=Decimal("0"),
        monthly_budget=Decimal("0"),
    )
    result = await quota_registry.reserve_capacity(request_no_limit)
    assert result.reserved is False
    assert result.reason == "no_limits_configured"


@pytest.mark.asyncio
async def test_get_global_budget_includes_reservations(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "daily_budget": "50.0",
        "monthly_budget": "500.0",
        "daily_spend": "10.0",
        "monthly_spend": "100.0",
        "reserved_daily_cost": "5.0",
        "reserved_monthly_cost": "50.0",
        "updated_at": "2024-01-15T10:30:00+00:00",
    }
    quota_registry._client = mock_client

    state = await quota_registry.get_global_budget()
    assert state.reserved_daily_cost == Decimal("5.0")
    assert state.reserved_monthly_cost == Decimal("50.0")
    assert state.daily_remaining == Decimal("35.0")
    assert state.monthly_remaining == Decimal("350.0")


@pytest.mark.asyncio
async def test_reservation_key_format() -> None:
    assert _reservation_key("abc-123") == "ai:provider-quota:reservation:abc-123"


@pytest.mark.asyncio
async def test_expire_reservations_marks_old_pending_as_expired(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()

    async def _gen(*args: object, **kwargs: object):
        yield "ai:provider-quota:reservation:res-1"

    mock_client.scan_iter = MagicMock(return_value=_gen())
    mock_client.eval.return_value = "expired"
    quota_registry._client = mock_client

    count = await quota_registry.expire_reservations(max_age_seconds=3600)
    assert count == 1


@pytest.mark.asyncio
async def test_expire_reservations_skips_non_pending(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()

    async def _gen(*args: object, **kwargs: object):
        yield "ai:provider-quota:reservation:res-1"

    mock_client.scan_iter = MagicMock(return_value=_gen())
    mock_client.eval.return_value = "already_settled"
    quota_registry._client = mock_client

    count = await quota_registry.expire_reservations(max_age_seconds=3600)
    assert count == 0


@pytest.mark.asyncio
async def test_list_outstanding_reservations_filters_by_status(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    mock_client = AsyncMock()

    async def _gen(*args: object, **kwargs: object):
        yield "ai:provider-quota:reservation:res-1"
        yield "ai:provider-quota:reservation:res-2"

    mock_client.scan_iter = MagicMock(return_value=_gen())

    call_count = [0]

    async def _hgetall(key):
        call_count[0] += 1
        if call_count[0] == 1:
            return {
                "reservation_id": "res-1",
                "provider_id": "openai",
                "window": "day",
                "status": "pending",
                "created_at": "2024-01-15T10:30:00+00:00",
                "updated_at": "2024-01-15T10:30:00+00:00",
            }
        return {
            "reservation_id": "res-2",
            "provider_id": "openai",
            "window": "day",
            "status": "settled",
            "created_at": "2024-01-15T10:30:00+00:00",
            "updated_at": "2024-01-15T10:30:00+00:00",
        }

    mock_client.hgetall.side_effect = _hgetall
    quota_registry._client = mock_client

    reservations = await quota_registry.list_outstanding_reservations()
    assert len(reservations) == 1
    assert reservations[0].reservation_id == "res-1"
    assert reservations[0].status == ReservationStatus.PENDING


# ======================================================================
# Reservation recovery tests
# ======================================================================


@pytest.mark.asyncio
async def test_reconcile_reservations_no_expired_returns_zero(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """When no expired reservations exist, reconcile returns 0."""
    mock_client = AsyncMock()

    async def _gen(*args: object, **kwargs: object):
        yield "ai:provider-quota:reservation:res-1"

    mock_client.scan_iter = MagicMock(return_value=_gen())
    mock_client.eval.return_value = "pending"
    quota_registry._client = mock_client

    count = await quota_registry.reconcile_reservations(max_age_seconds=3600)
    assert count == 0


@pytest.mark.asyncio
async def test_reconcile_reservations_releases_expired(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """Expired reservations are released, freeing capacity."""
    mock_client = AsyncMock()

    def _make_gen(**kwargs: object):
        async def _gen(**_: object):
            yield "ai:provider-quota:reservation:res-1"
            yield "ai:provider-quota:reservation:res-2"

        return _gen()

    mock_client.scan_iter = MagicMock(side_effect=_make_gen)

    def _eval_side_effect(script, numkeys, *args):
        if script == _MARK_EXPIRED_LUA:
            return "expired"
        return "released"

    mock_client.eval.side_effect = _eval_side_effect
    mock_client.hgetall.side_effect = lambda key: {
        "reservation_id": f"res-{key[-1]}",
        "provider_id": "openai",
        "window": "day",
        "status": "expired",
        "created_at": "2024-01-15T10:30:00+00:00",
        "updated_at": "2024-01-15T11:30:00+00:00",
        "expired_at": "2024-01-15T11:30:00+00:00",
    }
    quota_registry._client = mock_client

    count = await quota_registry.reconcile_reservations(max_age_seconds=3600)
    assert count == 2
    release_calls = [
        call.args for call in mock_client.eval.call_args_list if call.args[0] != _MARK_EXPIRED_LUA
    ]
    assert len(release_calls) == 2


@pytest.mark.asyncio
async def test_reconcile_reservations_skips_non_expired_outstanding(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """Non-expired (pending) reservations are not released during reconciliation."""
    mock_client = AsyncMock()

    async def _gen(*args: object, **kwargs: object):
        yield "ai:provider-quota:reservation:res-1"

    mock_client.scan_iter = MagicMock(return_value=_gen())
    mock_client.eval.return_value = "pending"
    quota_registry._client = mock_client

    count = await quota_registry.reconcile_reservations(max_age_seconds=3600)
    assert count == 0


@pytest.mark.asyncio
async def test_release_reservation_releases_expired_status(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """Release can recover an expired reservation, freeing reserved capacity."""
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "window": "day",
        "status": "expired",
    }
    mock_client.eval.return_value = "released"
    quota_registry._client = mock_client

    result = await quota_registry.release_reservation("res-1")
    assert result.released is True
    assert result.reason == "released"


@pytest.mark.asyncio
async def test_expire_reservations_passes_extended_ttl(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """Expired reservations receive an extended TTL for the recovery window."""
    mock_client = AsyncMock()

    async def _gen(*args: object, **kwargs: object):
        yield "ai:provider-quota:reservation:res-1"

    mock_client.scan_iter = MagicMock(return_value=_gen())
    mock_client.eval.return_value = "expired"
    quota_registry._client = mock_client

    await quota_registry.expire_reservations(max_age_seconds=3600)

    eval_calls = [call.args for call in mock_client.eval.call_args_list]
    mark_expired_call = next(c for c in eval_calls if c[0] == _MARK_EXPIRED_LUA)
    assert mark_expired_call[1] == 1
    assert mark_expired_call[-2] == str(_RESERVATION_TTL_SECONDS)
    assert mark_expired_call[-1] == str(_RESERVATION_EXPIRED_TTL_SECONDS)


@pytest.mark.asyncio
async def test_get_reservation_includes_expired_at(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """Reservation state includes the expired_at timestamp when present."""
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "reservation_id": "res-1",
        "provider_id": "openai",
        "window": "day",
        "request_count": "1",
        "input_tokens": "100",
        "output_tokens": "50",
        "total_tokens": "150",
        "estimated_cost": "0.003",
        "status": "expired",
        "created_at": "2024-01-15T10:30:00+00:00",
        "updated_at": "2024-01-15T11:30:00+00:00",
        "expired_at": "2024-01-15T11:30:00+00:00",
    }
    quota_registry._client = mock_client

    state = await quota_registry.get_reservation("res-1")
    assert state is not None
    assert state.status == ReservationStatus.EXPIRED
    assert state.expired_at is not None


# ======================================================================
# Settlement / release race tests
# ======================================================================


@pytest.mark.asyncio
async def test_settle_expired_reservation_does_not_record_usage(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """Settling an expired reservation must not record actual usage or charge budget.

    A provider response arriving after the reservation was expired is an
    indeterminate outcome — the provider *may* have processed the request,
    but the capacity accounting has already been flagged for release.
    The settlement should report ``settled=False`` so the caller can decide
    whether to log or alert, without corrupting counters.
    """
    mock_client = AsyncMock()
    mock_client.eval.return_value = "already_expired"
    quota_registry._client = mock_client

    usage = ProviderUsage(provider_id="openai", window=QuotaWindow.DAY)
    result = await quota_registry.settle_reservation("res-expired", usage, actual_cost=0.004)
    assert result.settled is False
    assert result.reason == "already_expired"


@pytest.mark.asyncio
async def test_settle_after_release_is_idempotent(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """A late settlement arriving after release must not double-decrement.

    The Lua script returns ``already_released`` and the release-side counters
    are left untouched.
    """
    mock_client = AsyncMock()
    mock_client.eval.return_value = "already_released"
    quota_registry._client = mock_client

    usage = ProviderUsage(provider_id="openai", window=QuotaWindow.DAY)
    result = await quota_registry.settle_reservation("res-1", usage, actual_cost=0.004)
    assert result.settled is True
    assert result.reason == "already_released"


@pytest.mark.asyncio
async def test_release_after_settlement_is_safe_noop(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """Releasing a settled reservation must not refund consumed capacity."""
    mock_client = AsyncMock()
    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "window": "day",
    }
    mock_client.eval.return_value = "already_settled"
    quota_registry._client = mock_client

    result = await quota_registry.release_reservation("res-1")
    assert result.released is True
    assert result.reason == "already_settled"


@pytest.mark.asyncio
async def test_reconcile_reservations_respects_batch_limit(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """``batch_limit`` caps the number of releases per reconciliation cycle."""
    mock_client = AsyncMock()

    def _make_gen(**_kwargs: object):
        async def _gen(**__: object):
            for i in range(5):
                yield f"ai:provider-quota:reservation:res-{i}"

        return _gen()

    mock_client.scan_iter = MagicMock(side_effect=_make_gen)

    def _eval_side_effect(script, numkeys, *args):
        if script == _MARK_EXPIRED_LUA:
            return "expired"
        if script == _RELEASE_RESERVATION_LUA:
            return "released"
        return "unknown"

    mock_client.eval.side_effect = _eval_side_effect
    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "window": "day",
        "status": "expired",
    }
    quota_registry._client = mock_client

    count = await quota_registry.reconcile_reservations(max_age_seconds=3600, batch_limit=2)
    assert count == 2


@pytest.mark.asyncio
async def test_reconcile_reservations_survives_individual_release_failure(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """A release error for one reservation must not abort the entire batch."""
    mock_client = AsyncMock()

    def _make_gen(**_kwargs: object):
        async def _gen(**__: object):
            yield "ai:provider-quota:reservation:res-1"
            yield "ai:provider-quota:reservation:res-2"

        return _gen()

    mock_client.scan_iter = MagicMock(side_effect=_make_gen)

    eval_calls = [0]

    def _eval_side_effect(script, numkeys, *args):
        eval_calls[0] += 1
        if script == _MARK_EXPIRED_LUA:
            return "expired"
        if script == _RELEASE_RESERVATION_LUA:
            if eval_calls[0] == 3:
                raise RedisError("transient")
            return "released"
        return "unknown"

    mock_client.eval.side_effect = _eval_side_effect
    mock_client.hgetall.return_value = {
        "provider_id": "openai",
        "window": "day",
        "status": "expired",
    }
    quota_registry._client = mock_client

    count = await quota_registry.reconcile_reservations(max_age_seconds=3600)
    assert count == 1
    assert eval_calls[0] >= 4


@pytest.mark.asyncio
async def test_list_outstanding_includes_pending_and_expired_only(
    quota_registry: RedisProviderQuotaRegistry,
) -> None:
    """Only PENDING and EXPIRED reservations are outstanding; settled/released are excluded."""
    mock_client = AsyncMock()

    def _make_gen(**_kwargs: object):
        async def _gen(**__: object):
            yield "ai:provider-quota:reservation:res-1"
            yield "ai:provider-quota:reservation:res-2"
            yield "ai:provider-quota:reservation:res-3"

        return _gen()

    mock_client.scan_iter = MagicMock(side_effect=_make_gen)
    mock_client.hgetall.side_effect = lambda key: {
        "reservation_id": f"res-{key[-1]}",
        "provider_id": "openai",
        "window": "day",
        "status": {
            "ai:provider-quota:reservation:res-1": "pending",
            "ai:provider-quota:reservation:res-2": "expired",
            "ai:provider-quota:reservation:res-3": "settled",
        }[key],
        "request_count": "1",
        "input_tokens": "10",
        "output_tokens": "5",
        "total_tokens": "15",
        "estimated_cost": "0.001",
        "created_at": "2024-01-15T10:30:00+00:00",
        "updated_at": "2024-01-15T10:30:00+00:00",
    }
    quota_registry._client = mock_client

    outstanding = await quota_registry.list_outstanding_reservations()
    assert len(outstanding) == 2
    statuses = {r.status for r in outstanding}
    assert ReservationStatus.SETTLED not in statuses


__all__ = [
    "test_check_quota_eligible_when_no_limits",
    "test_check_quota_eligible_when_under_limit",
    "test_check_quota_excluded_when_request_limit_exhausted",
    "test_check_quota_with_explicit_limit_fails_open_on_redis_error",
    "test_check_quota_with_explicit_limit_reports_exhaustion",
    "test_check_quota_with_explicit_limit_skips_quota_read",
    "test_expire_reservations_marks_old_pending_as_expired",
    "test_expire_reservations_passes_extended_ttl",
    "test_expire_reservations_skips_non_pending",
    "test_get_global_budget_defaults",
    "test_get_global_budget_includes_reservations",
    "test_get_provider_quota_returns_none_when_absent",
    "test_get_reservation_includes_expired_at",
    "test_get_reservation_returns_none_when_absent",
    "test_get_reservation_returns_state",
    "test_list_outstanding_includes_pending_and_expired_only",
    "test_list_outstanding_reservations_filters_by_status",
    "test_provider_quota_key",
    "test_provider_usage_key",
    "test_reconcile_reservations_no_expired_returns_zero",
    "test_reconcile_reservations_releases_expired",
    "test_reconcile_reservations_respects_batch_limit",
    "test_reconcile_reservations_skips_non_expired_outstanding",
    "test_reconcile_reservations_survives_individual_release_failure",
    "test_record_usage_success",
    "test_release_after_settlement_cannot_refund",
    "test_release_after_settlement_is_safe_noop",
    "test_release_reservation_idempotent",
    "test_release_reservation_not_found_is_noop",
    "test_release_reservation_releases_expired_status",
    "test_release_reservation_success",
    "test_reservation_key_format",
    "test_reserve_capacity_already_reserved_is_idempotent",
    "test_reserve_capacity_fails_closed_on_redis_error",
    "test_reserve_capacity_fails_closed_with_no_limits",
    "test_reserve_capacity_rejects_daily_budget_exceeded",
    "test_reserve_capacity_rejects_monthly_budget_exceeded",
    "test_reserve_capacity_rejects_provider_cost_limit_exceeded",
    "test_reserve_capacity_rejects_request_limit_exceeded",
    "test_reserve_capacity_rejects_token_limit_exceeded",
    "test_reserve_capacity_success",
    "test_set_and_get_provider_quota",
    "test_settle_after_release_is_idempotent",
    "test_settle_expired_reservation_does_not_record_usage",
    "test_settle_reservation_does_not_release_settled",
    "test_settle_reservation_idempotent_on_duplicate",
    "test_settle_reservation_success",
    "test_update_global_budget",
    "test_window_id_day",
    "test_window_id_hour",
    "test_window_id_minute",
    "test_window_id_month",
]
