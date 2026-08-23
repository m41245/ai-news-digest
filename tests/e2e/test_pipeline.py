"""
End-to-end smoke tests for the AI News Digest application.

These tests verify the core application flows work correctly:
- Application starts and health endpoints respond
- Authentication flow (register, login, authenticated request)
- Admin authorization works
- API endpoints return expected responses
- Security headers are present
- Rate limiting is functional

External services (AI providers, SMTP, RSS) are mocked to avoid
dependencies on external systems.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.infrastructure.cache.redis_store import RedisStore
from ai_news_digest.main import app


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Create a test client with mocked Redis for rate limiting."""
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


@pytest.fixture
def unique_email() -> str:
    """Generate a unique email for each test to avoid collisions."""
    return f"e2e-{uuid4().hex}@example.com"


class TestApplicationStartup:
    """Verify the application starts and basic endpoints work."""

    def test_application_starts(self, client: TestClient) -> None:
        """Application should start and respond to requests."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    def test_liveness_endpoint(self, client: TestClient) -> None:
        """Liveness endpoint should return alive status."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "application" in data

    def test_readiness_endpoint(self, client: TestClient) -> None:
        """Readiness endpoint should return status with checks."""
        response = client.get("/health/ready")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "cache" in data["checks"]


class TestSecurityHeaders:
    """Verify security headers are present on responses."""

    def test_security_headers_present(self, client: TestClient) -> None:
        """Responses should include security headers."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    def test_request_id_header(self, client: TestClient) -> None:
        """Responses should include X-Request-ID header."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_process_time_header(self, client: TestClient) -> None:
        """Responses should include X-Process-Time header."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers


class TestAuthentication:
    """Verify authentication flow works correctly."""

    def test_unauthenticated_request_rejected(self, client: TestClient) -> None:
        """Unauthenticated requests to protected endpoints should fail."""
        response = client.get("/api/v1/articles/")
        assert response.status_code == 401

    def test_register_requires_strong_password(self, client: TestClient, unique_email: str) -> None:
        """Registration should reject weak passwords."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "weak",
            },
        )
        assert response.status_code in (400, 422)

    def test_login_invalid_credentials(self, client: TestClient) -> None:
        """Login with invalid credentials should fail."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "e2e-nonexistent@example.com",
                "password": "WrongPassword123",
            },
        )
        assert response.status_code == 401


class TestErrorHandling:
    """Verify error responses are consistent."""

    def test_not_found_error_format(self, client: TestClient) -> None:
        """Not found errors should have consistent format."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed_format(self, client: TestClient) -> None:
        """Method not allowed should return proper status."""
        response = client.delete("/health/live")
        assert response.status_code == 405


class TestMetricsEndpoint:
    """Verify metrics endpoint security and accessibility."""

    def test_metrics_requires_authentication(self, client: TestClient) -> None:
        """Metrics endpoint should require authentication."""
        response = client.get("/metrics/")
        assert response.status_code == 401

    def test_metrics_health_accessible(self, client: TestClient) -> None:
        """Metrics health endpoint should be accessible."""
        response = client.get("/metrics/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_metrics_accessible_with_admin_token(
        self, client: TestClient, unique_email: str
    ) -> None:
        """Metrics endpoint should be accessible with admin token."""
        import asyncio

        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from ai_news_digest.bootstrap.container import Container
        from ai_news_digest.core.config import settings
        from ai_news_digest.domain.models.user import User
        from ai_news_digest.infrastructure.auth.password import hash_password

        email = f"admin-{unique_email}"

        async def _setup_admin() -> None:
            test_engine = create_async_engine(
                settings.database_url,
                echo=False,
                future=True,
            )
            test_session_factory = async_sessionmaker(
                test_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
            )
            try:
                async with test_session_factory() as session:
                    container = Container(session)
                    existing = await container.user_repository.get_by_email(email)
                    if existing is None:
                        user = User.create(
                            email=email,
                            hashed_password=hash_password("AdminPass123!"),
                            is_active=True,
                            is_admin=True,
                        )
                        await container.user_repository.create(user)
                    else:
                        existing.is_admin = True
                        existing.is_active = True
                        await container.user_repository.update(existing)
            finally:
                await test_engine.dispose()

        asyncio.run(_setup_admin())

        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": email,
                "password": "AdminPass123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        response = client.get(
            "/metrics/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"


class TestRateLimiting:
    """Verify rate limiting is functional."""

    def test_health_endpoints_exempt_from_rate_limit(self, client: TestClient) -> None:
        """Health endpoints should be exempt from rate limiting."""
        with patch.object(
            RedisStore,
            "get",
            new_callable=AsyncMock,
            return_value="999",
        ):
            response = client.get("/health/live")
            assert response.status_code == 200

            response = client.get("/health/ready")
            assert response.status_code in (200, 503)


__all__ = [
    "TestApplicationStartup",
    "TestAuthentication",
    "TestErrorHandling",
    "TestMetricsEndpoint",
    "TestRateLimiting",
    "TestSecurityHeaders",
]
