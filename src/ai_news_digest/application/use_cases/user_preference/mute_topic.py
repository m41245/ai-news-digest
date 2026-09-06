from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.ports.user_preference_repository import UserPreferenceRepository


class MuteTopicUseCase:
    def __init__(self, preference_repository: UserPreferenceRepository) -> None:
        self._preference_repository = preference_repository

    async def execute(self, current_user: User, topic_id: UUID) -> None:
        await self._preference_repository.add_muted_topic(current_user.id, topic_id)


class UnmuteTopicUseCase:
    def __init__(self, preference_repository: UserPreferenceRepository) -> None:
        self._preference_repository = preference_repository

    async def execute(self, current_user: User, topic_id: UUID) -> None:
        await self._preference_repository.remove_muted_topic(current_user.id, topic_id)
