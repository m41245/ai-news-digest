"""
Unit tests for metrics endpoint authentication and metric collection.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from ai_news_digest.core import metrics as core_metrics
from ai_news_digest.infrastructure.cache.redis_store import RedisStore
from ai_news_digest.main import app


class _StubSettings:
    """Minimal settings stub used to exercise the IP allow-list guard."""

    def __init__(self, allowed: list[str]) -> None:
        self.metrics_allowed_ips = allowed


def _make_request(client_ip: str | None, forwarded: str | None = None) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if forwarded is not None:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    scope: dict = {
        "type": "http",
        "headers": headers,
        "client": ("127.0.0.1", 1234) if client_ip is None else (client_ip, 1234),
    }
    return Request(scope)


@pytest.fixture
def client() -> TestClient:
    """Create a test client with mocked Redis."""
    with (
        patch.object(
            RedisStore,
            "get",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch.object(
            RedisStore,
            "set",
            new_callable=AsyncMock,
            return_value=None,
        ),
        TestClient(app) as test_client,
    ):
        yield test_client


class TestMetricsEndpoint:
    """Tests for metrics endpoint authentication."""

    def test_metrics_requires_bearer_token(self, client: TestClient) -> None:
        """Metrics endpoint should reject requests without Bearer token."""
        response = client.get("/metrics/")
        assert response.status_code == 401
        body = response.json()
        error_text = " ".join(str(v).lower() for v in body.values())
        assert "authentic" in error_text

    def test_metrics_rejects_invalid_token(self, client: TestClient) -> None:
        """Metrics endpoint should reject invalid Bearer tokens."""
        response = client.get(
            "/metrics/",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401
        body = response.json()
        error_text = " ".join(str(v).lower() for v in body.values())
        assert "authentic" in error_text

    def test_metrics_health_does_not_require_auth(self, client: TestClient) -> None:
        """Metrics health endpoint should be accessible without auth."""
        response = client.get("/metrics/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_metrics_rejects_non_admin_user(self, client: TestClient) -> None:
        """Metrics endpoint should reject non-admin users with 403."""
        from ai_news_digest.domain.models.user import User
        from ai_news_digest.infrastructure.auth.jwt import create_access_token

        non_admin_user = User(
            id="user-123",
            email="user@example.com",
            hashed_password="hashed",  # noqa: S106
            is_active=True,
            is_admin=False,
            created_at=datetime.now(UTC),
        )

        mock_session = MagicMock()
        mock_container = MagicMock()
        mock_container.user_repository.get_by_id = AsyncMock(return_value=non_admin_user)

        with (
            patch(
                "ai_news_digest.api.v1.dependencies.auth.get_db_session",
                return_value=mock_session,
            ),
            patch(
                "ai_news_digest.api.v1.dependencies.auth.Container",
                return_value=mock_container,
            ),
        ):
            token = create_access_token(subject="user-123")
            response = client.get(
                "/metrics/",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 403


def _auth_admin_client(client: TestClient) -> str:
    """Return an Authorization header for an admin user."""
    from ai_news_digest.domain.models.user import User
    from ai_news_digest.infrastructure.auth.jwt import create_access_token

    admin_user = User(
        id="admin-1",
        email="admin@example.com",
        hashed_password="hashed",  # noqa: S106
        is_active=True,
        is_admin=True,
        created_at=datetime.now(UTC),
    )
    mock_session = MagicMock()
    mock_container = MagicMock()
    mock_container.user_repository.get_by_id = AsyncMock(return_value=admin_user)
    token = create_access_token(subject="admin-1")
    return token, mock_session, mock_container


class TestApplicationMetrics:
    """Tests for the in-process application metric recording functions."""

    def test_article_collected_increments_snapshot(self) -> None:
        before = core_metrics.snapshot_application_metrics()["articles_collected_total"]
        core_metrics.record_article_collected(3)
        after = core_metrics.snapshot_application_metrics()["articles_collected_total"]
        assert after == before + 3

    def test_article_processed_deduplicated_and_digest(self) -> None:
        core_metrics.record_article_processed(2)
        core_metrics.record_article_deduplicated(1)
        core_metrics.record_digest_generated(1)
        snap = core_metrics.snapshot_application_metrics()
        assert snap["articles_processed_total"] >= 2
        assert snap["articles_deduplicated_total"] >= 1
        assert snap["digests_generated_total"] >= 1

    def test_ai_failure_and_latency_are_recorded(self) -> None:
        core_metrics.record_ai_failure("openai")
        core_metrics.record_ai_latency("openai", 0.5)
        snap = core_metrics.snapshot_application_metrics()
        failures = snap["ai_provider_failures_total"]
        assert isinstance(failures, dict)
        assert failures.get("openai", 0) >= 1
        latencies = snap["ai_processing_latencies"]
        assert isinstance(latencies, dict)
        assert "openai" in latencies

    def test_ai_request_count_is_recorded(self) -> None:
        core_metrics.record_ai_request("openai")
        core_metrics.record_ai_request("openai")
        snap = core_metrics.snapshot_application_metrics()
        requests = snap["ai_provider_requests_total"]
        assert isinstance(requests, dict)
        assert requests.get("openai", 0) >= 2

    def test_rss_ingestion_metrics_are_recorded(self) -> None:
        core_metrics.record_rss_ingestion_success("feed-1")
        core_metrics.record_rss_ingestion_failure("feed-1")
        core_metrics.record_rss_ingestion_success("feed-2")
        snap = core_metrics.snapshot_application_metrics()
        success = snap["rss_ingestion_success_total"]
        failure = snap["rss_ingestion_failure_total"]
        assert isinstance(success, dict)
        assert isinstance(failure, dict)
        assert success.get("feed-1", 0) >= 1
        assert success.get("feed-2", 0) >= 1
        assert failure.get("feed-1", 0) >= 1

    def test_email_delivery_metrics_are_recorded(self) -> None:
        core_metrics.record_email_delivery_success(3)
        core_metrics.record_email_delivery_failure(1)
        snap = core_metrics.snapshot_application_metrics()
        assert snap["email_delivery_success_total"] >= 3
        assert snap["email_delivery_failure_total"] >= 1


class TestRedisBackedCeleryMetrics:
    """Tests for the cross-process Redis-backed Celery counters."""

    @pytest.fixture
    def mock_redis(self) -> MagicMock:
        client = MagicMock()
        client.incr = AsyncMock(return_value=1)
        client.incrbyfloat = AsyncMock(return_value=1.0)
        client.mget = AsyncMock(return_value=["5", "2", "1", "12.5", "5"])
        client.aclose = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_counters_use_redis_incr(self, mock_redis: MagicMock) -> None:
        with patch.object(core_metrics, "_build_redis_client", return_value=mock_redis):
            await core_metrics.record_celery_task_success("t")
            await core_metrics.record_celery_task_failure("t")
            await core_metrics.record_celery_task_retry("t")
            await core_metrics.record_celery_task_duration("t", 1.5)

        assert mock_redis.incr.await_count == 4
        mock_redis.incrbyfloat.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_read_celery_metrics_aggregates(self, mock_redis: MagicMock) -> None:
        with patch.object(core_metrics, "_build_redis_client", return_value=mock_redis):
            result = await core_metrics.read_celery_metrics()

        assert result["task_success_total"] == 5.0
        assert result["task_failure_total"] == 2.0
        assert result["task_retries_total"] == 1.0
        assert result["task_duration_sum"] == 12.5
        assert result["task_duration_count"] == 5.0

    @pytest.mark.asyncio
    async def test_recorded_metrics_survive_redis_failure(self) -> None:
        client = MagicMock()
        client.incr = AsyncMock(side_effect=RuntimeError("boom"))
        client.aclose = AsyncMock()
        with patch.object(core_metrics, "_build_redis_client", return_value=client):
            # Should not raise even if Redis is unavailable.
            await core_metrics.record_celery_task_success("t")
            result = await core_metrics.read_celery_metrics()

        assert result["task_success_total"] == 0.0


class TestDbPoolMetrics:
    """Tests for the database pool metric extraction."""

    def test_get_pool_metrics_exposes_active_idle_overflow(self) -> None:
        from ai_news_digest.infrastructure.database.session import get_pool_metrics

        metrics = get_pool_metrics()
        assert "active" in metrics
        assert "idle" in metrics
        assert "overflow" in metrics
        # active + idle should equal the configured pool size unless overflowed.
        assert metrics["active"] >= 0
        assert metrics["idle"] >= 0


class TestMetricsEndpointContent:
    """Tests that the authenticated endpoint exposes the new metrics."""

    def test_endpoint_exposes_new_metrics(self, client: TestClient) -> None:
        token, mock_session, mock_container = _auth_admin_client(client)
        with (
            patch(
                "ai_news_digest.api.v1.dependencies.auth.get_db_session",
                return_value=mock_session,
            ),
            patch(
                "ai_news_digest.api.v1.dependencies.auth.Container",
                return_value=mock_container,
            ),
        ):
            response = client.get(
                "/metrics/",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        body = response.text
        for expected in (
            "articles_collected_total",
            "articles_processed_total",
            "articles_deduplicated_total",
            "digests_generated_total",
            "ai_provider_requests_total",
            "ai_provider_failures_total",
            "rss_ingestion_success_total",
            "rss_ingestion_failure_total",
            "email_delivery_success_total",
            "email_delivery_failure_total",
            "db_pool_connections_active",
            "db_pool_connections_idle",
            "db_pool_overflow",
            "redis_connected",
        ):
            assert expected in body


class TestMetricsIpRestriction:
    """Tests for the optional IP allow-list guard."""

    def test_empty_allow_list_permits(self) -> None:
        from ai_news_digest.api.metrics import require_metrics_ip_access

        stub = _StubSettings(allowed=[])
        with patch("ai_news_digest.api.metrics.settings", stub):
            # Should not raise when no allow-list is configured.
            require_metrics_ip_access(_make_request("203.0.113.9"))

    def test_disallowed_ip_raises(self) -> None:
        from fastapi.exceptions import HTTPException

        from ai_news_digest.api.metrics import require_metrics_ip_access

        stub = _StubSettings(allowed=["10.0.0.1"])
        with (
            patch("ai_news_digest.api.metrics.settings", stub),
            pytest.raises(HTTPException),
        ):
            require_metrics_ip_access(_make_request("203.0.113.9"))

    def test_allowed_ip_permits(self) -> None:
        from ai_news_digest.api.metrics import require_metrics_ip_access

        stub = _StubSettings(allowed=["10.0.0.1", "203.0.113.9"])
        with patch("ai_news_digest.api.metrics.settings", stub):
            require_metrics_ip_access(_make_request("203.0.113.9"))

    def test_forwarded_header_is_respected(self) -> None:
        from fastapi.exceptions import HTTPException

        from ai_news_digest.api.metrics import require_metrics_ip_access

        stub = _StubSettings(allowed=["10.0.0.1"])
        with (
            patch("ai_news_digest.api.metrics.settings", stub),
            pytest.raises(HTTPException),
        ):
            require_metrics_ip_access(_make_request("127.0.0.1", forwarded="203.0.113.9, 10.0.0.1"))


class TestMetricsPathNormalization:
    """Tests for _get_normalized_path preventing cardinality explosion."""

    def test_matched_route_uses_template_path(self) -> None:
        """When a route is matched, the template path is used (not raw path)."""
        from ai_news_digest.api.metrics import _get_normalized_path

        mock_route = MagicMock()
        mock_route.path = "/api/v1/articles/{article_id}"
        scope = {"route": mock_route, "path": "/api/v1/articles/abc-123"}

        result = _get_normalized_path(scope)

        assert result == "/api/v1/articles/{article_id}"

    def test_unmatched_route_returns_generic_label(self) -> None:
        """When no route is matched (404), a generic 'unmatched' label is used."""
        from ai_news_digest.api.metrics import _get_normalized_path

        scope = {"route": None, "path": "/arbitrary/random/path/that/should/not/create/a/metric"}

        result = _get_normalized_path(scope)

        assert result == "unmatched"

    def test_missing_route_key_returns_unmatched(self) -> None:
        """When scope has no route or path, returns 'unmatched'."""
        from ai_news_digest.api.metrics import _get_normalized_path

        scope: dict = {}

        result = _get_normalized_path(scope)

        assert result == "unmatched"

    def test_route_without_path_attr_returns_unmatched(self) -> None:
        """When route object lacks a path attribute, returns 'unmatched'."""
        from ai_news_digest.api.metrics import _get_normalized_path

        mock_route = MagicMock()
        del mock_route.path  # remove the auto-created attribute
        scope = {"route": mock_route, "path": "/some/path"}

        result = _get_normalized_path(scope)

        assert result == "unmatched"

    def test_prevents_path_cardinality_explosion(self) -> None:
        """Verify that many different 404 paths all map to the same label."""
        from ai_news_digest.api.metrics import _get_normalized_path

        paths = [
            "/random-path-1",
            "/random-path-2",
            "/another/arbitrary/path",
            "/admin/secret",
            "/api/v1/nonexistent/endpoint/xyz",
        ]
        results = {_get_normalized_path({"route": None, "path": p}) for p in paths}

        assert results == {"unmatched"}


__all__ = [
    "TestApplicationMetrics",
    "TestDbPoolMetrics",
    "TestMetricsEndpoint",
    "TestMetricsEndpointContent",
    "TestMetricsIpRestriction",
    "TestMetricsPathNormalization",
    "TestRedisBackedCeleryMetrics",
]
