from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.ports.user_preference_repository import UserPreferenceRepository


class UnfollowCompanyUseCase:
    def __init__(self, preference_repository: UserPreferenceRepository) -> None:
        self._preference_repository = preference_repository

    async def execute(self, current_user: User, company_id: UUID) -> None:
        await self._preference_repository.remove_followed_company(current_user.id, company_id)
