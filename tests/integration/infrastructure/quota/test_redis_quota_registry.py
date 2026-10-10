"""
Real Redis integration tests for the quota reservation lifecycle.

These tests start an isolated Redis container via testcontainers and exercise
the actual Lua scripts — verifying atomicity, idempotency, and fail-closed
behaviour against a real Redis server.  They are marked ``integration`` so
they are excluded from the default unit-test run.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from ai_news_digest.application.ai.quota import (
    ProviderQuotaConfig,
    ProviderUsage,
    QuotaLimit,
    QuotaReservationRequest,
    QuotaWindow,
    ReservationStatus,
)
from ai_news_digest.infrastructure.quota.redis_provider_quota_registry import (
    _RESERVATION_EXPIRED_TTL_SECONDS,
    _RESERVATION_TTL_SECONDS,
    RedisProviderQuotaRegistry,
    _global_budget_key,
    _reservation_key,
)


def _quota_config(
    token_limit: int = 10_000,
    request_limit: int = 1_000,
) -> ProviderQuotaConfig:
    return ProviderQuotaConfig(
        provider_id="openai",
        limits=[
            QuotaLimit(
                window=QuotaWindow.DAY,
                request_limit=request_limit,
                token_limit=token_limit,
                cost_limit=Decimal("100.0"),
            )
        ],
    )


def _limit(
    token_limit: int | None = 300,
    request_limit: int | None = 10_000,
    cost_limit: Decimal | None = Decimal("100.0"),
) -> QuotaLimit:
    return QuotaLimit(
        window=QuotaWindow.DAY,
        request_limit=request_limit,
        token_limit=token_limit,
        cost_limit=cost_limit,
    )


def _reservation_request(
    reservation_id: str = "test-res",
    input_tokens: int = 100,
    output_tokens: int = 50,
    estimated_cost: Decimal = Decimal("0.003"),
    daily_budget: Decimal = Decimal("100.0"),
    monthly_budget: Decimal = Decimal("1000.0"),
    limit: QuotaLimit | None = None,
) -> QuotaReservationRequest:
    total = input_tokens + output_tokens
    if limit is None:
        limit = _limit()
    return QuotaReservationRequest(
        reservation_id=reservation_id,
        provider_id="openai",
        window=QuotaWindow.DAY,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total,
        estimated_cost=estimated_cost,
        cost_known=True,
        limit=limit,
        daily_budget=daily_budget,
        monthly_budget=monthly_budget,
    )


@pytest.fixture
def redis_registry(redis_container: object) -> RedisProviderQuotaRegistry:
    host = redis_container.get_container_host_ip()  # type: ignore[attr-defined]
    port = redis_container.get_exposed_port(6379)  # type: ignore[attr-defined]
    return RedisProviderQuotaRegistry(redis_url=f"redis://{host}:{port}/0")


@pytest.fixture(autouse=True)
async def _flush_registry(redis_registry: RedisProviderQuotaRegistry) -> None:
    client = await redis_registry._get_client()
    await client.flushdb()  # type: ignore[attr-defined]


@pytest.mark.integration
class TestRedisQuotaReservationLifecycle:
    """End-to-end tests of the reservation lifecycle against real Redis."""

    async def test_reserve_capacity_atomically_updates_counters(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(_quota_config())

        request = _reservation_request("res-1")
        result = await redis_registry.reserve_capacity(request)
        assert result.reserved is True
        assert result.reservation_id == "res-1"

        state = await redis_registry.get_reservation("res-1")
        assert state is not None
        assert state.status == ReservationStatus.PENDING
        assert state.input_tokens == 100

    async def test_concurrent_reservations_respect_token_limit(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(
            _quota_config(token_limit=300, request_limit=10_000)
        )

        result1 = await redis_registry.reserve_capacity(_reservation_request("res-1", 100, 50))
        assert result1.reserved is True

        result2 = await redis_registry.reserve_capacity(_reservation_request("res-2", 100, 50))
        assert result2.reserved is True

        result3 = await redis_registry.reserve_capacity(
            _reservation_request("res-3", 100, 50, limit=_limit(token_limit=300))
        )
        assert result3.reserved is False

    async def test_duplicate_reservation_id_is_idempotent(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(_quota_config())

        request = _reservation_request("dup-res")
        result1 = await redis_registry.reserve_capacity(request)
        assert result1.reserved is True

        result2 = await redis_registry.reserve_capacity(request)
        assert result2.reserved is True
        assert result2.reason == "already_reserved"

    async def test_settle_replaces_estimated_with_actual(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(_quota_config(token_limit=10_000))

        await redis_registry.reserve_capacity(_reservation_request("res-1"))

        usage = ProviderUsage(
            provider_id="openai",
            window=QuotaWindow.DAY,
            input_tokens=80,
            output_tokens=30,
            request_count=1,
        )
        result = await redis_registry.settle_reservation("res-1", usage, actual_cost=0.002)
        assert result.settled is True

        state = await redis_registry.get_reservation("res-1")
        assert state is not None
        assert state.status == ReservationStatus.SETTLED

    async def test_settlement_is_idempotent(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(_quota_config())

        await redis_registry.reserve_capacity(_reservation_request("res-1"))

        usage = ProviderUsage(
            provider_id="openai",
            window=QuotaWindow.DAY,
            input_tokens=80,
            output_tokens=30,
            request_count=1,
        )
        result1 = await redis_registry.settle_reservation("res-1", usage, actual_cost=0.002)
        assert result1.settled is True

        result2 = await redis_registry.settle_reservation("res-1", usage, actual_cost=0.002)
        assert result2.settled is True
        assert result2.reason == "already_settled"

    async def test_release_frees_capacity(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(
            _quota_config(token_limit=200, request_limit=10_000)
        )

        request = _reservation_request("res-1", 100, 50, limit=_limit(token_limit=200))
        await redis_registry.reserve_capacity(request)

        result = await redis_registry.release_reservation("res-1")
        assert result.released is True

        state = await redis_registry.get_reservation("res-1")
        assert state is not None
        assert state.status == ReservationStatus.RELEASED

        # After release, capacity should be available again
        result2 = await redis_registry.reserve_capacity(
            _reservation_request("res-2", 100, 50, limit=_limit(token_limit=200))
        )
        assert result2.reserved is True

    async def test_release_is_idempotent(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(_quota_config())

        await redis_registry.reserve_capacity(_reservation_request("res-1"))

        result1 = await redis_registry.release_reservation("res-1")
        assert result1.released is True

        result2 = await redis_registry.release_reservation("res-1")
        assert result2.released is True
        assert result2.reason == "already_released"

    async def test_settle_after_release_is_idempotent(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(_quota_config())

        await redis_registry.reserve_capacity(_reservation_request("res-1"))
        await redis_registry.release_reservation("res-1")

        usage = ProviderUsage(
            provider_id="openai",
            window=QuotaWindow.DAY,
            input_tokens=80,
            output_tokens=30,
            request_count=1,
        )
        result = await redis_registry.settle_reservation("res-1", usage, actual_cost=0.002)
        assert result.settled is True
        assert result.reason == "already_released"

    async def test_release_after_settlement_is_safe_noop(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(_quota_config())

        await redis_registry.reserve_capacity(_reservation_request("res-1"))
        await redis_registry.settle_reservation(
            "res-1",
            ProviderUsage(
                provider_id="openai",
                window=QuotaWindow.DAY,
                input_tokens=80,
                output_tokens=30,
            ),
            actual_cost=0.002,
        )

        result = await redis_registry.release_reservation("res-1")
        assert result.released is True
        assert result.reason == "already_settled"

    async def test_reconciliation_releases_expired_reservations(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(
            _quota_config(token_limit=200, request_limit=10_000)
        )

        request = _reservation_request("old-res", 100, 50, limit=_limit(token_limit=200))
        await redis_registry.reserve_capacity(request)

        # Backdate created_at so the reservation is considered "old"
        res_key = _reservation_key("old-res")
        old_ts = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        client = await redis_registry._get_client()
        await client.hset(name=res_key, mapping={"created_at": old_ts})

        count = await redis_registry.reconcile_reservations(max_age_seconds=3600, batch_limit=100)
        assert count == 1

        state = await redis_registry.get_reservation("old-res")
        assert state is not None
        assert state.status == ReservationStatus.RELEASED

        # Capacity should be freed for a new reservation
        result = await redis_registry.reserve_capacity(
            _reservation_request("new-res", 100, 50, limit=_limit(token_limit=200))
        )
        assert result.reserved is True

    async def test_reconciliation_respects_batch_limit(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(_quota_config(token_limit=10_000))

        old_ts = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        for i in range(5):
            res_id = f"old-res-{i}"
            await redis_registry.reserve_capacity(
                _reservation_request(res_id, 10, 5, Decimal("0.001"))
            )
            res_key = _reservation_key(res_id)
            client = await redis_registry._get_client()
            await client.hset(name=res_key, mapping={"created_at": old_ts})

        count1 = await redis_registry.reconcile_reservations(max_age_seconds=3600, batch_limit=2)
        assert count1 == 2

        count2 = await redis_registry.reconcile_reservations(max_age_seconds=3600, batch_limit=10)
        assert count2 == 3

    async def test_quota_exhausted_blocks_reservation(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(_quota_config(token_limit=50, request_limit=10_000))

        result1 = await redis_registry.reserve_capacity(
            _reservation_request("res-1", 50, 0, limit=_limit(token_limit=50))
        )
        assert result1.reserved is True

        result2 = await redis_registry.reserve_capacity(
            _reservation_request("res-2", 50, 0, limit=_limit(token_limit=50))
        )
        assert result2.reserved is False

    async def test_daily_budget_exhausted_blocks_reservation(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(_quota_config(token_limit=10_000))

        # Set up budget state where daily spend already equals the daily budget
        budget_key = _global_budget_key()
        client = await redis_registry._get_client()
        await client.hset(
            name=budget_key,
            mapping={
                "daily_budget": "10.0",
                "monthly_budget": "1000.0",
                "daily_spend": "10.0",
                "monthly_spend": "0.0",
            },
        )

        result = await redis_registry.reserve_capacity(
            _reservation_request(
                "res-1",
                daily_budget=Decimal("10.0"),
                monthly_budget=Decimal("1000.0"),
            )
        )
        assert result.reserved is False
        assert result.reason == "daily_budget_exhausted"

    async def test_settle_expired_reservation_does_not_record_usage(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        """A late provider response arriving after expiry must not corrupt counters."""
        await redis_registry.set_provider_quota(
            _quota_config(token_limit=200, request_limit=10_000)
        )

        request = _reservation_request("old-res", 100, 50, limit=_limit(token_limit=200))
        await redis_registry.reserve_capacity(request)

        res_key = _reservation_key("old-res")
        old_ts = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        client = await redis_registry._get_client()
        await client.hset(name=res_key, mapping={"created_at": old_ts})

        # Expire the reservation (do NOT release)
        await redis_registry.expire_reservations(max_age_seconds=3600)

        # A late settlement attempt should fail and NOT record actual usage
        usage = ProviderUsage(
            provider_id="openai",
            window=QuotaWindow.DAY,
            input_tokens=80,
            output_tokens=30,
            request_count=1,
        )
        result = await redis_registry.settle_reservation("old-res", usage, actual_cost=0.002)
        assert result.settled is False
        assert result.reason == "already_expired"

        # Capacity should still be held until reconcile releases it
        result2 = await redis_registry.reserve_capacity(
            _reservation_request("new-res", 100, 50, limit=_limit(token_limit=200))
        )
        assert result2.reserved is False

        # After reconciliation, capacity is freed
        count = await redis_registry.reconcile_reservations(max_age_seconds=3600, batch_limit=100)
        assert count == 1

        result3 = await redis_registry.reserve_capacity(
            _reservation_request("new-res2", 100, 50, limit=_limit(token_limit=200))
        )
        assert result3.reserved is True


@pytest.mark.integration
class TestRedisQuotaReconciliation:
    """Tests for reservation expiry and TTL behaviour."""

    async def test_reservation_ttl_sufficient_for_reconciliation(self) -> None:
        """Reservation TTL must outlive the max_age window to prevent capacity leaks."""
        assert _RESERVATION_TTL_SECONDS >= _RESERVATION_EXPIRED_TTL_SECONDS
        assert _RESERVATION_EXPIRED_TTL_SECONDS >= 86400

    async def test_expired_reservation_key_retains_extended_ttl(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(_quota_config())
        await redis_registry.reserve_capacity(_reservation_request("old-res"))

        expired = await redis_registry.expire_reservations(max_age_seconds=0)
        assert expired == 1

        key = _reservation_key("old-res")
        client = await redis_registry._get_client()
        ttl = await client.ttl(key)  # type: ignore[attr-defined]
        assert ttl > 0
        assert ttl >= _RESERVATION_EXPIRED_TTL_SECONDS - 10

    async def test_reconciliation_is_idempotent(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        await redis_registry.set_provider_quota(_quota_config())
        await redis_registry.reserve_capacity(_reservation_request("old-res"))

        res_key = _reservation_key("old-res")
        old_ts = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        client = await redis_registry._get_client()
        await client.hset(name=res_key, mapping={"created_at": old_ts})

        count1 = await redis_registry.reconcile_reservations(max_age_seconds=3600, batch_limit=100)
        assert count1 == 1

        count2 = await redis_registry.reconcile_reservations(max_age_seconds=3600, batch_limit=100)
        assert count2 == 0

    async def test_reconciliation_debits_spend_for_indeterminate_outcome(
        self,
        redis_registry: RedisProviderQuotaRegistry,
    ) -> None:
        """Releasing an indeterminate (expired) reservation must not under-count spend.

        An indeterminate provider outcome (timeout / lost settlement) leaves a
        reservation PENDING; reconciliation ages it to expired and releases it.
        Releasing frees reserved capacity, but the provider may still have
        billed — so the reserved estimate is conservatively debited to
        daily/monthly spend, keeping the global budget consistent and preventing
        over-issuance of the daily/monthly budget.
        """
        await redis_registry.set_provider_quota(
            _quota_config(token_limit=200, request_limit=10_000)
        )

        budget_key = _global_budget_key()
        client = await redis_registry._get_client()
        await client.hset(
            name=budget_key,
            mapping={
                "daily_budget": "100.0",
                "monthly_budget": "1000.0",
                "daily_spend": "0.0",
                "monthly_spend": "0.0",
                "reserved_daily_cost": "0.0",
                "reserved_monthly_cost": "0.0",
            },
        )

        request = _reservation_request(
            "ind-res", 100, 50, Decimal("1.0"), limit=_limit(token_limit=200)
        )
        assert (await redis_registry.reserve_capacity(request)).reserved is True

        budget = await redis_registry.get_global_budget()
        assert budget.daily_spend == Decimal("0")
        assert budget.reserved_daily_cost == Decimal("1")

        res_key = _reservation_key("ind-res")
        old_ts = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        await client.hset(name=res_key, mapping={"created_at": old_ts})

        count = await redis_registry.reconcile_reservations(max_age_seconds=3600, batch_limit=100)
        assert count == 1

        budget = await redis_registry.get_global_budget()
        # Capacity is reclaimed ...
        assert budget.reserved_daily_cost == Decimal("0")
        # ... and the reserved estimate is debited as spend (no under-count).
        assert budget.daily_spend == Decimal("1")
        assert budget.monthly_spend == Decimal("1")

        state = await redis_registry.get_reservation("ind-res")
        assert state is not None
        assert state.status == ReservationStatus.RELEASED
