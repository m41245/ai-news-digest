from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.user_preference import UserPreferenceProfile
from ai_news_digest.domain.ports.user_preference_repository import (
    UserPreferenceRepository as UserPreferenceRepositoryPort,
)
from ai_news_digest.infrastructure.database.mappers.user_preference_mapper import (
    UserPreferenceMapper,
)
from ai_news_digest.infrastructure.database.models.user_followed_category_model import (
    UserFollowedCategoryModel,
)
from ai_news_digest.infrastructure.database.models.user_followed_company_model import (
    UserFollowedCompanyModel,
)
from ai_news_digest.infrastructure.database.models.user_followed_topic_model import (
    UserFollowedTopicModel,
)
from ai_news_digest.infrastructure.database.models.user_model import UserModel
from ai_news_digest.infrastructure.database.models.user_muted_category_model import (
    UserMutedCategoryModel,
)
from ai_news_digest.infrastructure.database.models.user_muted_company_model import (
    UserMutedCompanyModel,
)
from ai_news_digest.infrastructure.database.models.user_muted_topic_model import (
    UserMutedTopicModel,
)
from ai_news_digest.infrastructure.database.models.user_preference_model import (
    UserPreferenceProfileModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class UserPreferenceRepository(
    BaseRepository[UserPreferenceProfileModel],
    UserPreferenceRepositoryPort,
):
    """SQLAlchemy implementation of the UserPreferenceRepository port."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_user_id(
        self,
        user_id: UUID,
    ) -> UserPreferenceProfile | None:
        statement = (
            select(UserModel)
            .options(
                selectinload(UserModel.preference_profile),
                selectinload(UserModel.followed_companies),
                selectinload(UserModel.followed_topics),
                selectinload(UserModel.followed_categories),
                selectinload(UserModel.muted_companies),
                selectinload(UserModel.muted_topics),
                selectinload(UserModel.muted_categories),
            )
            .where(UserModel.id == str(user_id))
        )

        result = await self._session.execute(statement)
        user = result.scalar_one_or_none()

        if user is None:
            return None

        profile_model = user.preference_profile
        if profile_model is None:
            profile_model = UserPreferenceProfileModel(
                user_id=str(user_id),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

        return UserPreferenceMapper.to_domain(
            profile_model,
            followed_companies=user.followed_companies,
            followed_topics=user.followed_topics,
            followed_categories=user.followed_categories,
            muted_companies=user.muted_companies,
            muted_topics=user.muted_topics,
            muted_categories=user.muted_categories,
        )

    async def create(
        self,
        profile: UserPreferenceProfile,
    ) -> UserPreferenceProfile:
        model = UserPreferenceMapper.to_model(profile)
        model = await self._add_and_refresh(model)
        return UserPreferenceMapper.to_domain(model)

    async def update(
        self,
        profile: UserPreferenceProfile,
    ) -> UserPreferenceProfile:
        statement = select(UserPreferenceProfileModel).where(
            UserPreferenceProfileModel.user_id == str(profile.user_id),
        )

        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            raise ResourceNotFoundError(
                f"UserPreferenceProfile for user '{profile.user_id}' was not found."
            )

        UserPreferenceMapper.update_model(model, profile)
        await self._commit()
        model = await self._refresh(model)

        return UserPreferenceMapper.to_domain(model)

    async def _ensure_profile(self, user_id: UUID) -> UserPreferenceProfileModel:
        statement = select(UserPreferenceProfileModel).where(
            UserPreferenceProfileModel.user_id == str(user_id),
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            model = UserPreferenceProfileModel(
                user_id=str(user_id),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self._session.add(model)
            await self._flush()

        return model

    async def add_followed_company(
        self,
        user_id: UUID,
        company_id: UUID,
    ) -> None:
        model = await self._ensure_profile(user_id)
        link = UserFollowedCompanyModel(
            user_id=str(user_id),
            company_id=str(company_id),
        )
        self._session.add(link)
        model.updated_at = datetime.now(UTC)
        await self._commit()

    async def remove_followed_company(
        self,
        user_id: UUID,
        company_id: UUID,
    ) -> None:
        statement = delete(UserFollowedCompanyModel).where(
            UserFollowedCompanyModel.user_id == str(user_id),
            UserFollowedCompanyModel.company_id == str(company_id),
        )
        await self._session.execute(statement)
        model = await self._ensure_profile(user_id)
        model.updated_at = datetime.now(UTC)
        await self._commit()

    async def add_followed_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> None:
        model = await self._ensure_profile(user_id)
        link = UserFollowedTopicModel(
            user_id=str(user_id),
            topic_id=str(topic_id),
        )
        self._session.add(link)
        model.updated_at = datetime.now(UTC)
        await self._commit()

    async def remove_followed_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> None:
        statement = delete(UserFollowedTopicModel).where(
            UserFollowedTopicModel.user_id == str(user_id),
            UserFollowedTopicModel.topic_id == str(topic_id),
        )
        await self._session.execute(statement)
        model = await self._ensure_profile(user_id)
        model.updated_at = datetime.now(UTC)
        await self._commit()

    async def add_followed_category(
        self,
        user_id: UUID,
        category_id: UUID,
    ) -> None:
        model = await self._ensure_profile(user_id)
        link = UserFollowedCategoryModel(
            user_id=str(user_id),
            category_id=str(category_id),
        )
        self._session.add(link)
        model.updated_at = datetime.now(UTC)
        await self._commit()

    async def remove_followed_category(
        self,
        user_id: UUID,
        category_id: UUID,
    ) -> None:
        statement = delete(UserFollowedCategoryModel).where(
            UserFollowedCategoryModel.user_id == str(user_id),
            UserFollowedCategoryModel.category_id == str(category_id),
        )
        await self._session.execute(statement)
        model = await self._ensure_profile(user_id)
        model.updated_at = datetime.now(UTC)
        await self._commit()

    async def add_muted_company(
        self,
        user_id: UUID,
        company_id: UUID,
    ) -> None:
        model = await self._ensure_profile(user_id)
        link = UserMutedCompanyModel(
            user_id=str(user_id),
            company_id=str(company_id),
        )
        self._session.add(link)
        model.updated_at = datetime.now(UTC)
        await self._commit()

    async def remove_muted_company(
        self,
        user_id: UUID,
        company_id: UUID,
    ) -> None:
        statement = delete(UserMutedCompanyModel).where(
            UserMutedCompanyModel.user_id == str(user_id),
            UserMutedCompanyModel.company_id == str(company_id),
        )
        await self._session.execute(statement)
        model = await self._ensure_profile(user_id)
        model.updated_at = datetime.now(UTC)
        await self._commit()

    async def add_muted_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> None:
        model = await self._ensure_profile(user_id)
        link = UserMutedTopicModel(
            user_id=str(user_id),
            topic_id=str(topic_id),
        )
        self._session.add(link)
        model.updated_at = datetime.now(UTC)
        await self._commit()

    async def remove_muted_topic(
        self,
        user_id: UUID,
        topic_id: UUID,
    ) -> None:
        statement = delete(UserMutedTopicModel).where(
            UserMutedTopicModel.user_id == str(user_id),
            UserMutedTopicModel.topic_id == str(topic_id),
        )
        await self._session.execute(statement)
        model = await self._ensure_profile(user_id)
        model.updated_at = datetime.now(UTC)
        await self._commit()

    async def add_muted_category(
        self,
        user_id: UUID,
        category_id: UUID,
    ) -> None:
        model = await self._ensure_profile(user_id)
        link = UserMutedCategoryModel(
            user_id=str(user_id),
            category_id=str(category_id),
        )
        self._session.add(link)
        model.updated_at = datetime.now(UTC)
        await self._commit()

    async def remove_muted_category(
        self,
        user_id: UUID,
        category_id: UUID,
    ) -> None:
        statement = delete(UserMutedCategoryModel).where(
            UserMutedCategoryModel.user_id == str(user_id),
            UserMutedCategoryModel.category_id == str(category_id),
        )
        await self._session.execute(statement)
        model = await self._ensure_profile(user_id)
        model.updated_at = datetime.now(UTC)
        await self._commit()

    async def delete_by_user_id(
        self,
        user_id: UUID,
    ) -> None:
        await self._session.execute(
            delete(UserFollowedCompanyModel).where(
                UserFollowedCompanyModel.user_id == str(user_id),
            )
        )
        await self._session.execute(
            delete(UserFollowedTopicModel).where(
                UserFollowedTopicModel.user_id == str(user_id),
            )
        )
        await self._session.execute(
            delete(UserFollowedCategoryModel).where(
                UserFollowedCategoryModel.user_id == str(user_id),
            )
        )
        await self._session.execute(
            delete(UserMutedCompanyModel).where(
                UserMutedCompanyModel.user_id == str(user_id),
            )
        )
        await self._session.execute(
            delete(UserMutedTopicModel).where(
                UserMutedTopicModel.user_id == str(user_id),
            )
        )
        await self._session.execute(
            delete(UserMutedCategoryModel).where(
                UserMutedCategoryModel.user_id == str(user_id),
            )
        )
        await self._session.execute(
            delete(UserPreferenceProfileModel).where(
                UserPreferenceProfileModel.user_id == str(user_id),
            )
        )
        await self._commit()
