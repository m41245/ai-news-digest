from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.infrastructure.database.base import Base
from ai_news_digest.infrastructure.database.models.story_cluster_model import (
    StoryClusterModel,
)
from ai_news_digest.infrastructure.database.models.user_model import UserModel

if TYPE_CHECKING:
    from ai_news_digest.infrastructure.database.models.user_collection_model import (
        UserCollectionModel,
    )


class SavedStoryModel(Base):
    """Database representation of a user-saved story."""

    __tablename__ = "saved_stories"

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

    collection_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_collections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[UserModel] = relationship(
        back_populates="saved_stories",
        lazy="selectin",
    )

    story_cluster: Mapped[StoryClusterModel] = relationship(
        lazy="selectin",
    )

    collection: Mapped[UserCollectionModel | None] = relationship(
        back_populates="saved_stories",
        lazy="selectin",
    )
