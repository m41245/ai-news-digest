from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.infrastructure.database.base import Base
from ai_news_digest.infrastructure.database.models.saved_story_model import (
    SavedStoryModel,
)
from ai_news_digest.infrastructure.database.models.user_model import UserModel


class UserCollectionModel(Base):
    """Database representation of a user collection."""

    __tablename__ = "user_collections"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    user: Mapped[UserModel] = relationship(
        back_populates="collections",
        lazy="selectin",
    )

    saved_stories: Mapped[list[SavedStoryModel]] = relationship(
        back_populates="collection",
        lazy="selectin",
    )
