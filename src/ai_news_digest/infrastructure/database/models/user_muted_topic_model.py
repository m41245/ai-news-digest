from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    from ai_news_digest.infrastructure.database.models.topic_model import TopicModel
    from ai_news_digest.infrastructure.database.models.user_model import UserModel


class UserMutedTopicModel(Base):
    __tablename__ = "user_muted_topics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    user: Mapped[UserModel] = relationship(back_populates="muted_topics", lazy="selectin")
    topic: Mapped[TopicModel] = relationship(back_populates="muted_by_users", lazy="selectin")
