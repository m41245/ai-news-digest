"""
Unit tests for UserPreferenceRepository.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from ai_news_digest.infrastructure.database.repositories.user_preference_repository import (
    UserPreferenceRepository,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute.return_value = result
    session.flush.return_value = None
    session.commit.return_value = None
    session.refresh.return_value = None
    return session


@pytest.fixture
def repository(mock_session) -> UserPreferenceRepository:
    return UserPreferenceRepository(mock_session)


class TestUserPreferenceRepository:
    @pytest.mark.asyncio
    async def test_get_by_user_id_none(self, repository) -> None:
        result = await repository.get_by_user_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_create(self, repository, mock_session) -> None:
        profile = MagicMock()
        profile.user_id = uuid4()
        model = MagicMock()
        with patch(
            "ai_news_digest.infrastructure.database.repositories.user_preference_repository.UserPreferenceMapper"
        ) as mapper:
            mapper.to_model.return_value = model
            mapper.to_domain.return_value = profile
            result = await repository.create(profile)
        assert result is profile

    @pytest.mark.asyncio
    async def test_ensure_profile_creates(self, repository, mock_session) -> None:
        uid = uuid4()
        # execute returns None -> creates profile
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        model = await repository._ensure_profile(uid)
        assert model is not None

    @pytest.mark.asyncio
    async def test_follow_and_mute_methods(self, repository, mock_session) -> None:
        uid = uuid4()
        cid = uuid4()
        tid = uuid4()
        cat = uuid4()
        sid = uuid4()
        # ensure profile returns existing model
        prof = MagicMock()
        prof.updated_at = None
        mock_session.execute.return_value.scalar_one_or_none.return_value = prof

        await repository.add_followed_company(uid, cid)
        await repository.remove_followed_company(uid, cid)
        await repository.add_followed_topic(uid, tid)
        await repository.remove_followed_topic(uid, tid)
        await repository.add_followed_category(uid, cat)
        await repository.remove_followed_category(uid, cat)
        await repository.add_muted_company(uid, cid)
        await repository.remove_muted_company(uid, cid)
        await repository.add_muted_topic(uid, tid)
        await repository.remove_muted_topic(uid, tid)
        await repository.add_muted_category(uid, cat)
        await repository.remove_muted_category(uid, cat)
        await repository.add_followed_source(uid, sid)
        await repository.remove_followed_source(uid, sid)
        await repository.add_muted_source(uid, sid)
        await repository.remove_muted_source(uid, sid)

    @pytest.mark.asyncio
    async def test_update_and_delete(self, repository, mock_session) -> None:
        profile = MagicMock()
        profile.user_id = uuid4()
        model = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = model
        with patch(
            "ai_news_digest.infrastructure.database.repositories.user_preference_repository.UserPreferenceMapper"
        ) as mapper:
            mapper.to_domain.return_value = profile
            await repository.update(profile)
        await repository.delete_by_user_id(profile.user_id)


__all__ = ["TestUserPreferenceRepository"]
