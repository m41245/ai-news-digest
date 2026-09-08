from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    from ai_news_digest.infrastructure.database.models.article_topic_model import (
        ArticleTopicModel,
    )
    from ai_news_digest.infrastructure.database.models.user_followed_topic_model import (
        UserFollowedTopicModel,
    )
    from ai_news_digest.infrastructure.database.models.user_muted_topic_model import (
        UserMutedTopicModel,
    )


class TopicModel(Base):
    __tablename__ = "topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate="now()", nullable=False
    )

    article_links: Mapped[list[ArticleTopicModel]] = relationship(
        back_populates="topic", cascade="all, delete-orphan", lazy="selectin"
    )
    followed_by_users: Mapped[list[UserFollowedTopicModel]] = relationship(
        back_populates="topic", lazy="selectin"
    )
    muted_by_users: Mapped[list[UserMutedTopicModel]] = relationship(
        back_populates="topic", lazy="selectin"
    )
