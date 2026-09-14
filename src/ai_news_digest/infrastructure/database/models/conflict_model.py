from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_news_digest.domain.enums.conflict_status import ConflictStatus
from ai_news_digest.domain.enums.conflict_type import ConflictType
from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    pass


class ConflictModel(Base):
    """Database representation of a detected claim conflict."""

    __tablename__ = "conflicts"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    claim_a_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    claim_b_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    article_a_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    article_b_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    source_a_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    source_b_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    conflict_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=ConflictType.OTHER.value,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=ConflictStatus.POTENTIAL.value,
        index=True,
    )

    confidence: Mapped[float] = mapped_column(
        nullable=False,
    )

    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    detection_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    story_cluster_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    same_source: Mapped[bool] = mapped_column(
        nullable=False,
        server_default="false",
    )

    conflict_metadata: Mapped[str | None] = mapped_column(
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


__all__ = ["ConflictModel"]
