from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_news_digest.core.exceptions import ResourceNotFoundError
from ai_news_digest.domain.models.user import User
from ai_news_digest.domain.ports.user_repository import (
    UserRepository as UserRepositoryPort,
)
from ai_news_digest.infrastructure.database.mappers.user_mapper import (
    UserMapper,
)
from ai_news_digest.infrastructure.database.models.user_model import (
    UserModel,
)
from ai_news_digest.infrastructure.database.repositories.base_repository import (
    BaseRepository,
)


class UserRepository(
    BaseRepository[UserModel],
    UserRepositoryPort,
):
    """SQLAlchemy implementation of the UserRepository port."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        super().__init__(session)

    async def create(
        self,
        user: User,
    ) -> User:
        """Persist a new user."""
        model = UserMapper.to_model(user)
        model = await self._add_and_refresh(model)
        return UserMapper.to_domain(model)

    async def get_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        """Retrieve a user by its identifier."""
        statement = select(UserModel).where(UserModel.id == str(user_id))

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return UserMapper.to_domain(model)

    async def get_by_email(
        self,
        email: str,
    ) -> User | None:
        """Retrieve a user by its email address."""
        statement = select(UserModel).where(UserModel.email == email)

        result = await self._session.execute(statement)

        model = result.scalar_one_or_none()

        if model is None:
            return None

        return UserMapper.to_domain(model)

    async def list_all(
        self,
    ) -> list[User]:
        """Return all users ordered by creation time (oldest first)."""
        statement = select(UserModel).order_by(UserModel.created_at.asc())
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [UserMapper.to_domain(model) for model in models]

    async def update(
        self,
        user: User,
    ) -> User:
        """Persist changes to an existing user."""
        statement = select(UserModel).where(UserModel.id == str(user.id))
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            raise ResourceNotFoundError(f"User with id '{user.id}' was not found.")

        UserMapper.update_model(model, user)
        await self._commit()
        model = await self._refresh(model)
        return UserMapper.to_domain(model)

    async def delete(
        self,
        user_id: UUID,
    ) -> None:
        """Delete a user by identifier."""
        statement = select(UserModel).where(UserModel.id == str(user_id))
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()

        if model is None:
            return

        await self._delete(model)
