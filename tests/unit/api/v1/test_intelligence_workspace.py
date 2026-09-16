"""
Backend integration tests for M96 intelligence workspace API endpoints.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from ai_news_digest.domain.models.story_cluster import StoryCluster
from ai_news_digest.domain.models.user import User
from ai_news_digest.infrastructure.auth.jwt import create_access_token
from ai_news_digest.infrastructure.database.models.story_cluster_model import StoryClusterModel
from ai_news_digest.infrastructure.database.models.user_model import UserModel


def _create_user(session) -> UserModel:
    user = UserModel(
        id=str(uuid4()),
        email="workspace-api@example.com",
        hashed_password="hashed",
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
