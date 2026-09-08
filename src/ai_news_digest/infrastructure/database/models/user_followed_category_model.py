from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    from ai_news_digest.infrastructure.database.models.category_model import CategoryModel
    from ai_news_digest.infrastructure.database.models.user_model import UserModel


class UserFollowedCategoryModel(Base):
    __tablename__ = "user_followed_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )

    user: Mapped[UserModel] = relationship(back_populates="followed_categories", lazy="selectin")
    category: Mapped[CategoryModel] = relationship(
        back_populates="followed_by_users", lazy="selectin"
    )
