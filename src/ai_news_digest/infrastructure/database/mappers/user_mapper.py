from __future__ import annotations

from uuid import UUID

from ai_news_digest.domain.models.user import User
from ai_news_digest.infrastructure.database.models.user_model import (
    UserModel,
)


class UserMapper:
    """Maps between User domain objects and UserModel ORM entities."""

    @staticmethod
    def to_model(user: User) -> UserModel:
        """Convert a domain User into an ORM UserModel."""
        return UserModel(
            id=str(user.id),
            email=user.email,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
        )

    @staticmethod
    def to_domain(model: UserModel) -> User:
        """Convert an ORM UserModel into a domain User."""
        return User(
            id=UUID(model.id),
            email=model.email,
            hashed_password=model.hashed_password,
            is_active=model.is_active,
            is_admin=model.is_admin,
            created_at=model.created_at,
        )

    @staticmethod
    def update_model(
        model: UserModel,
        user: User,
    ) -> None:
        """Update an existing ORM model from a domain User."""
        model.email = user.email
        model.hashed_password = user.hashed_password
        model.is_active = user.is_active
        model.is_admin = user.is_admin
