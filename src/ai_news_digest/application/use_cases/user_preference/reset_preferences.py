from __future__ import annotations

from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.ports.user_preference_repository import UserPreferenceRepository


class ResetPreferencesUseCase:
    """Reset all preferences for the current user to safe defaults."""

    def __init__(
        self,
        preference_repository: UserPreferenceRepository,
    ) -> None:
        self._preference_repository = preference_repository

    async def execute(
        self,
        current_user: User,
    ) -> None:
        await self._preference_repository.delete_by_user_id(current_user.id)
