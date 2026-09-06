from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_news_digest.infrastructure.database.base import Base


class UserPreferenceProfileModel(Base):
    """Database representation of a user's preference profile."""

    __tablename__ = "user_preference_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    min_importance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
    )

    min_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0.0",
    )

    feed_sort: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="published_at",
    )

    freshness_window_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    preferred_source_types_json: Mapped[str | None] = mapped_column(
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
