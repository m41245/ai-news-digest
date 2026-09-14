from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.domain.enums.claim_status import ClaimStatus
from ai_news_digest.domain.enums.claim_type import ClaimType
from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    from ai_news_digest.infrastructure.database.models.claim_evidence_model import (
        ClaimEvidenceModel,
    )


class ClaimModel(Base):
    """
    Database representation of an AI-extracted claim.
    """

    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    article_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    claim_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    claim_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=ClaimType.OTHER.value,
    )

    confidence: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=ClaimStatus.UNVERIFIED.value,
        index=True,
    )

    evidence_support_score: Mapped[float | None] = mapped_column(
        nullable=True,
    )

    schema_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="v1",
    )

    prompt_version: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    ai_provider: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    ai_model: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )

    processing_metadata: Mapped[str | None] = mapped_column(
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

    evidence_items: Mapped[list[ClaimEvidenceModel]] = relationship(
        back_populates="claim",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


__all__ = ["ClaimModel"]
