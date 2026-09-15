from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_news_digest.domain.enums.story_activity_status import StoryActivityStatus
from ai_news_digest.infrastructure.database.base import Base


class StoryActivityModel(Base):
    """
    Database representation of story activity detection results.
    """

    __tablename__ = "story_activity"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    story_cluster_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=StoryActivityStatus.STALE.value,
        index=True,
    )

    activity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0",
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0",
    )

    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default="",
    )

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    detection_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    article_count_recent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    unique_source_count_recent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    recent_article_velocity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0",
    )

    latest_article_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    first_article_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    recent_claim_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    recent_conflict_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    state_change_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
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


__all__ = ["StoryActivityModel"]
