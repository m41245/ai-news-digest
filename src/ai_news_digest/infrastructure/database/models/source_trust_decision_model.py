from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    pass


class SourceTrustDecisionModel(Base):
    __tablename__ = "source_trust_decisions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    source_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    actor_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    decision: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    previous_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    resulting_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    previous_is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    resulting_is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    validation_outcome: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
