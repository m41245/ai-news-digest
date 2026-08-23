"""
Unit tests for metrics endpoint authentication.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.infrastructure.cache.redis_store import RedisStore
from ai_news_digest.main import app


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
        assert response.json()["detail"] in ("Not authenticated", "Authentication required.")

    def test_metrics_rejects_invalid_token(self, client: TestClient) -> None:
        """Metrics endpoint should reject invalid Bearer tokens."""
        response = client.get(
            "/metrics/",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] in ("Not authenticated", "Authentication required.")

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


__all__ = ["TestMetricsEndpoint"]
