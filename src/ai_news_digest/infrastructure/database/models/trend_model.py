from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_news_digest.domain.enums.trend_status import TrendStatus
from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    pass


class TrendModel(Base):
    """
    Database representation of a detected trend.
    """

    __tablename__ = "trends"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    trend_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    canonical_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=TrendStatus.STALE.value,
    )

    trend_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0",
    )

    momentum_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        server_default="0",
    )

    first_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    last_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    recent_activity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    baseline_activity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    source_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    story_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
    )

    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    trend_metadata: Mapped[str | None] = mapped_column(
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


__all__ = ["TrendModel"]
