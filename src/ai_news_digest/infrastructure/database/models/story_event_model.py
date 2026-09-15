from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_news_digest.domain.enums.story_event_type import StoryEventType
from ai_news_digest.infrastructure.database.base import Base


class StoryEventModel(Base):
    __tablename__ = "story_events"

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

    event_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=StoryEventType.OTHER.value,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0",
    )

    event_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    representative_article_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )

    processing_metadata: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    schema_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="v1",
    )

    sequence: Mapped[int] = mapped_column(
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


__all__ = ["StoryEventModel"]
