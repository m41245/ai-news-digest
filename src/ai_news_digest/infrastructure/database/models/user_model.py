from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    from ai_news_digest.infrastructure.database.models.user_followed_category_model import (
        UserFollowedCategoryModel,
    )
    from ai_news_digest.infrastructure.database.models.user_followed_company_model import (
        UserFollowedCompanyModel,
    )
    from ai_news_digest.infrastructure.database.models.user_followed_topic_model import (
        UserFollowedTopicModel,
    )
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


class UserModel(Base):
    """
    Database representation of an application user.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    preference_profile: Mapped[UserPreferenceProfileModel | None] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    followed_companies: Mapped[list[UserFollowedCompanyModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    followed_topics: Mapped[list[UserFollowedTopicModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    followed_categories: Mapped[list[UserFollowedCategoryModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    muted_companies: Mapped[list[UserMutedCompanyModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    muted_topics: Mapped[list[UserMutedTopicModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    muted_categories: Mapped[list[UserMutedCategoryModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
