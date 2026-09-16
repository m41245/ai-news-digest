from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.infrastructure.database.base import Base
from ai_news_digest.infrastructure.database.models.story_cluster_model import (
    StoryClusterModel,
)
from ai_news_digest.infrastructure.database.models.user_model import UserModel


class FollowedStoryModel(Base):
    """Database representation of a user-followed story."""

    __tablename__ = "followed_stories"

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

    story_cluster_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("story_clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[UserModel] = relationship(
        back_populates="followed_stories",
        lazy="selectin",
    )

    story_cluster: Mapped[StoryClusterModel] = relationship(
        lazy="selectin",
    )
