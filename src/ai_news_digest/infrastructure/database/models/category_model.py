from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.infrastructure.database.base import Base
from ai_news_digest.infrastructure.database.models.article_category_model import (
    ArticleCategoryModel,
)
from ai_news_digest.infrastructure.database.models.article_model import (
    ArticleModel,
)
from ai_news_digest.infrastructure.database.models.user_followed_category_model import (
    UserFollowedCategoryModel,
)
from ai_news_digest.infrastructure.database.models.user_muted_category_model import (
    UserMutedCategoryModel,
)


class CategoryModel(Base):
    """
    Database representation of an article category.
    """

    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    articles: Mapped[list[ArticleModel]] = relationship(
        back_populates="category",
        lazy="selectin",
    )

    article_links: Mapped[list[ArticleCategoryModel]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    followed_by_users: Mapped[list[UserFollowedCategoryModel]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    muted_by_users: Mapped[list[UserMutedCategoryModel]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
