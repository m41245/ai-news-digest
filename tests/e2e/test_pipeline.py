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

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ai_news_digest.core.config import get_settings
from ai_news_digest.infrastructure.cache.redis_store import RedisStore
from ai_news_digest.infrastructure.database.base import Base
from ai_news_digest.infrastructure.database.models import (
    article_model,  # noqa: F401
    category_model,  # noqa: F401
    digest_article_model,  # noqa: F401
    digest_delivery_model,  # noqa: F401
    digest_model,  # noqa: F401
    source_model,  # noqa: F401
    user_model,  # noqa: F401
)
from ai_news_digest.infrastructure.database.session import (
    SessionLocal as _original_SessionLocal,
)
from ai_news_digest.infrastructure.database.session import (
    engine as _original_engine,
)
from ai_news_digest.main import app


@pytest.fixture(autouse=True)
async def _isolated_db_engine(postgres_container) -> AsyncGenerator[None, None]:
    """
    Give each E2E test its own database engine/connection pool backed by
    a dedicated PostgreSQL testcontainer.

    The global engine in ``session.py`` is shared across the entire test
    session. On Windows, asyncpg connection pools can leak state across
    event-loop boundaries, so we swap in a fresh engine for every test
    and dispose it deterministically.
    """
    import ai_news_digest.infrastructure.database.session as _session_module
    from ai_news_digest.core.config import settings as lazy_settings

    old_engine = _session_module.engine
    if old_engine is not None and old_engine is not _original_engine:
        await old_engine.dispose()

    container_url = postgres_container.get_connection_url(driver="asyncpg")
    real_settings = get_settings()
    original_db_url = real_settings.database_url
    object.__setattr__(lazy_settings, "database_url", container_url)
    object.__setattr__(real_settings, "database_url", container_url)

    test_engine = create_async_engine(
        container_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )
    test_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    _session_module.engine = test_engine
    _session_module.SessionLocal = test_session_factory

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield
    finally:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        _session_module.engine = _original_engine
        _session_module.SessionLocal = _original_SessionLocal
        object.__setattr__(lazy_settings, "database_url", original_db_url)
        object.__setattr__(real_settings, "database_url", original_db_url)
        await test_engine.dispose()


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
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
        patch.object(
            RedisStore,
            "ttl",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch.object(
            RedisStore,
            "delete",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as test_client:
            yield test_client


@pytest.fixture
def unique_email() -> str:
    """Generate a unique email for each test to avoid collisions."""
    return f"e2e-{uuid4().hex}@example.com"


class TestApplicationStartup:
    """Verify the application starts and basic endpoints work."""

    async def test_application_starts(self, client: AsyncClient) -> None:
        """Application should start and respond to requests."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data

    async def test_liveness_endpoint(self, client: AsyncClient) -> None:
        """Liveness endpoint should return alive status."""
        response = await client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "application" in data

    async def test_readiness_endpoint(self, client: AsyncClient) -> None:
        """Readiness endpoint should return status with checks."""
        response = await client.get("/health/ready")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "cache" in data["checks"]


class TestSecurityHeaders:
    """Verify security headers are present on responses."""

    async def test_security_headers_present(self, client: AsyncClient) -> None:
        """Responses should include security headers."""
        response = await client.get("/health/live")
        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    async def test_request_id_header(self, client: AsyncClient) -> None:
        """Responses should include X-Request-ID header."""
        response = await client.get("/health/live")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    async def test_process_time_header(self, client: AsyncClient) -> None:
        """Responses should include X-Process-Time header."""
        response = await client.get("/health/live")
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers


class TestAuthentication:
    """Verify authentication flow works correctly."""

    async def test_unauthenticated_request_rejected(self, client: AsyncClient) -> None:
        """Unauthenticated requests to protected endpoints should fail."""
        response = await client.get("/api/v1/articles/")
        assert response.status_code == 401

    async def test_register_requires_strong_password(
        self, client: AsyncClient, unique_email: str
    ) -> None:
        """Registration should reject weak passwords."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "weak",
            },
        )
        assert response.status_code in (400, 422)

    async def test_login_invalid_credentials(self, client: AsyncClient) -> None:
        """Login with invalid credentials should fail."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "e2e-nonexistent@example.com",
                "password": "WrongPassword123",
            },
        )
        assert response.status_code == 401


class TestErrorHandling:
    """Verify error responses are consistent."""

    async def test_not_found_error_format(self, client: AsyncClient) -> None:
        """Not found errors should have consistent format."""
        response = await client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    async def test_method_not_allowed_format(self, client: AsyncClient) -> None:
        """Method not allowed should return proper status."""
        response = await client.delete("/health/live")
        assert response.status_code == 405


class TestMetricsEndpoint:
    """Verify metrics endpoint security and accessibility."""

    async def test_metrics_requires_authentication(self, client: AsyncClient) -> None:
        """Metrics endpoint should require authentication."""
        response = await client.get("/metrics/")
        assert response.status_code == 401

    async def test_metrics_health_accessible(self, client: AsyncClient) -> None:
        """Metrics health endpoint should be accessible."""
        response = await client.get("/metrics/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    async def test_metrics_accessible_with_admin_token(
        self, client: AsyncClient, unique_email: str
    ) -> None:
        """Metrics endpoint should be accessible with admin token."""

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

        await _setup_admin()

        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": email,
                "password": "AdminPass123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        response = await client.get(
            "/metrics/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"


class TestRateLimiting:
    """Verify rate limiting is functional."""

    async def test_health_endpoints_exempt_from_rate_limit(self, client: AsyncClient) -> None:
        """Health endpoints should be exempt from rate limiting."""
        with patch.object(
            RedisStore,
            "get",
            new_callable=AsyncMock,
            return_value="999",
        ):
            response = await client.get("/health/live")
            assert response.status_code == 200

            response = await client.get("/health/ready")
            assert response.status_code in (200, 503)


class TestPublicEndpoints:
    """Verify the unauthenticated public product API surface."""

    async def test_public_articles_returns_enriched_article(self, client: AsyncClient) -> None:
        """Public articles endpoint returns processed articles with names."""
        from datetime import UTC, datetime

        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from ai_news_digest.bootstrap.container import Container
        from ai_news_digest.core.config import get_settings
        from ai_news_digest.domain.enums.article_status import ArticleStatus
        from ai_news_digest.domain.models.article import Article
        from ai_news_digest.domain.models.source import Source

        settings = get_settings()

        async def _seed() -> str:
            engine = create_async_engine(settings.database_url, future=True)
            factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            unique_path = f"{uuid4().hex[:12]}"
            try:
                async with factory() as session:
                    container = Container(session)

                    source = await container.source_repository.create(
                        Source(
                            id=uuid4(),
                            name=f"E2E Public Source {unique_path}",
                            feed_url=f"https://e2e-public.example.com/{unique_path}/feed.xml",
                            website_url=None,
                            description=None,
                            is_active=True,
                            created_at=datetime.now(UTC),
                        ),
                    )

                    article = await container.article_repository.create(
                        Article(
                            id=uuid4(),
                            title=f"E2E Public Article {unique_path}",
                            url=f"https://e2e-public.example.com/{unique_path}/article",
                            summary="E2E summary",
                            content=None,
                            source_id=source.id,
                            category_id=None,
                            published_at=datetime.now(UTC),
                            fetched_at=datetime.now(UTC),
                            status=ArticleStatus.READY,
                        ),
                    )
                    return str(article.id)
            finally:
                await engine.dispose()

        article_id = await _seed()

        response = await client.get("/api/v1/public/articles")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

        matched = next((i for i in data["items"] if i["id"] == article_id), None)
        assert matched is not None
        assert matched["title"].startswith("E2E Public Article")
        assert matched["source_name"] is not None
        assert matched["category_name"] is None
        assert "content" not in matched
        assert "source_id" not in matched

    async def test_public_endpoints_do_not_require_auth(self, client: AsyncClient) -> None:
        """Public endpoints must respond without any Authorization header."""
        response = await client.get("/api/v1/public/articles")
        assert response.status_code == 200

        response = await client.get("/api/v1/public/categories")
        assert response.status_code == 200

        response = await client.get("/api/v1/public/digests")
        assert response.status_code == 200

    async def test_public_article_not_found_returns_404(self, client: AsyncClient) -> None:
        """Requesting a non-existent public article returns 404."""
        response = await client.get(f"/api/v1/public/articles/{uuid4()}")
        assert response.status_code == 404


__all__ = [
    "TestApplicationStartup",
    "TestAuthentication",
    "TestErrorHandling",
    "TestMetricsEndpoint",
    "TestPublicEndpoints",
    "TestRateLimiting",
    "TestSecurityHeaders",
]
