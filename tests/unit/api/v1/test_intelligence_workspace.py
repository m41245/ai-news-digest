"""
Backend integration tests for M96 intelligence workspace API endpoints.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from ai_news_digest.api.middleware.exception_handler import setup_exception_handlers
from ai_news_digest.api.v1.dependencies.dependencies import get_container
from ai_news_digest.api.v1.routes.intelligence_workspace import router
from ai_news_digest.bootstrap.container import Container
from ai_news_digest.infrastructure.auth.jwt import create_access_token
from ai_news_digest.infrastructure.database.models.story_cluster_model import StoryClusterModel
from ai_news_digest.infrastructure.database.models.user_model import UserModel
from ai_news_digest.infrastructure.database.session import get_db_session


@pytest.fixture
def client(db_session: AsyncSession) -> TestClient:
    """Build a test client for the workspace router backed by the real database.

    This follows the established sibling route-test pattern: a bare ``FastAPI``
    app with only the router under test, exception handlers installed, and the
    session-bound dependencies overridden. Real JWT authentication is preserved
    (``get_current_active_user`` is *not* overridden), so the tests exercise the
    same auth path as production.

    ``TestClient`` serves the ASGI app from its own event loop while
    ``db_session`` belongs to the pytest-asyncio loop, so the app cannot reuse
    the test engine's pooled connections. A separate engine against the same
    database is created instead, using ``NullPool`` so every request opens and
    closes its own connection and nothing outlives the app's loop.
    """
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    engine = create_async_engine(
        db_session.bind.url.render_as_string(hide_password=False),
        poolclass=NullPool,
        future=True,
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    async def _override_container() -> AsyncGenerator[Container, None]:
        async with session_maker() as session:
            yield Container(session)

    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_container] = _override_container

    setup_exception_handlers(app)
    with TestClient(app) as test_client:
        yield test_client


def _create_user(session) -> UserModel:
    user = UserModel(
        id=str(uuid4()),
        email="workspace-api@example.com",
        hashed_password="hashed",  # noqa: S106 - test fixture, not a real secret
        is_active=True,
        is_admin=False,
    )
    session.add(user)
    return user


def _create_cluster(session) -> StoryClusterModel:
    cluster = StoryClusterModel(
        id=str(uuid4()),
        title="Workspace Test Cluster",
        slug="workspace-test-cluster",
        status="active",
    )
    session.add(cluster)
    return cluster


def _auth_headers(user: UserModel) -> dict[str, str]:
    token = create_access_token(subject=user.id)
    return {"Authorization": f"Bearer {token}"}


class TestSavedStoriesAPI:
    @pytest.mark.asyncio
    async def test_save_story(self, client: TestClient, db_session):
        user = _create_user(db_session)
        cluster = _create_cluster(db_session)
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(cluster)

        response = client.post(
            "/api/v1/me/saved-stories",
            json={"story_cluster_id": cluster.id},
            headers=_auth_headers(user),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["story_cluster_id"] == cluster.id
        assert data["user_id"] == user.id

    @pytest.mark.asyncio
    async def test_list_saved_stories(self, client: TestClient, db_session):
        user = _create_user(db_session)
        cluster = _create_cluster(db_session)
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(cluster)

        client.post(
            "/api/v1/me/saved-stories",
            json={"story_cluster_id": cluster.id},
            headers=_auth_headers(user),
        )

        response = client.get("/api/v1/me/saved-stories", headers=_auth_headers(user))
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["story_cluster_id"] == cluster.id

    @pytest.mark.asyncio
    async def test_unsave_story(self, client: TestClient, db_session):
        user = _create_user(db_session)
        cluster = _create_cluster(db_session)
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(cluster)

        client.post(
            "/api/v1/me/saved-stories",
            json={"story_cluster_id": cluster.id},
            headers=_auth_headers(user),
        )

        response = client.delete(
            f"/api/v1/me/saved-stories/{cluster.id}",
            headers=_auth_headers(user),
        )
        assert response.status_code == 204

        response = client.get("/api/v1/me/saved-stories", headers=_auth_headers(user))
        assert response.status_code == 200
        assert len(response.json()) == 0

    @pytest.mark.asyncio
    async def test_duplicate_save_returns_conflict(self, client: TestClient, db_session):
        user = _create_user(db_session)
        cluster = _create_cluster(db_session)
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(cluster)

        client.post(
            "/api/v1/me/saved-stories",
            json={"story_cluster_id": cluster.id},
            headers=_auth_headers(user),
        )

        response = client.post(
            "/api/v1/me/saved-stories",
            json={"story_cluster_id": cluster.id},
            headers=_auth_headers(user),
        )
        assert response.status_code == 409


class TestCollectionsAPI:
    @pytest.mark.asyncio
    async def test_create_collection(self, client: TestClient, db_session):
        user = _create_user(db_session)
        await db_session.commit()
        await db_session.refresh(user)

        response = client.post(
            "/api/v1/me/collections",
            json={"name": "Saved", "description": "My saved stories"},
            headers=_auth_headers(user),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Saved"
        assert data["user_id"] == user.id

    @pytest.mark.asyncio
    async def test_list_collections(self, client: TestClient, db_session):
        user = _create_user(db_session)
        await db_session.commit()
        await db_session.refresh(user)

        client.post(
            "/api/v1/me/collections",
            json={"name": "Saved"},
            headers=_auth_headers(user),
        )

        response = client.get("/api/v1/me/collections", headers=_auth_headers(user))
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_delete_collection(self, client: TestClient, db_session):
        user = _create_user(db_session)
        await db_session.commit()
        await db_session.refresh(user)

        create_resp = client.post(
            "/api/v1/me/collections",
            json={"name": "ToDelete"},
            headers=_auth_headers(user),
        )
        collection_id = create_resp.json()["id"]

        response = client.delete(
            f"/api/v1/me/collections/{collection_id}",
            headers=_auth_headers(user),
        )
        assert response.status_code == 204


class TestFollowedStoriesAPI:
    @pytest.mark.asyncio
    async def test_follow_story(self, client: TestClient, db_session):
        user = _create_user(db_session)
        cluster = _create_cluster(db_session)
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(cluster)

        response = client.post(
            f"/api/v1/me/followed-stories/{cluster.id}",
            headers=_auth_headers(user),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["story_cluster_id"] == cluster.id

    @pytest.mark.asyncio
    async def test_unfollow_story(self, client: TestClient, db_session):
        user = _create_user(db_session)
        cluster = _create_cluster(db_session)
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(cluster)

        client.post(
            f"/api/v1/me/followed-stories/{cluster.id}",
            headers=_auth_headers(user),
        )

        response = client.delete(
            f"/api/v1/me/followed-stories/{cluster.id}",
            headers=_auth_headers(user),
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_list_followed_stories(self, client: TestClient, db_session):
        user = _create_user(db_session)
        cluster = _create_cluster(db_session)
        await db_session.commit()
        await db_session.refresh(user)
        await db_session.refresh(cluster)

        client.post(
            f"/api/v1/me/followed-stories/{cluster.id}",
            headers=_auth_headers(user),
        )

        response = client.get("/api/v1/me/followed-stories", headers=_auth_headers(user))
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["story_cluster_id"] == cluster.id
