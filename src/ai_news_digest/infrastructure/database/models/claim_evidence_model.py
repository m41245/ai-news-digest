from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.domain.enums.evidence_strength import EvidenceStrength
from ai_news_digest.domain.enums.evidence_type import EvidenceType
from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    from ai_news_digest.infrastructure.database.models.claim_model import ClaimModel


class ClaimEvidenceModel(Base):
    """
    Database representation of evidence supporting a claim.

    Evidence references the source article without reproducing
    full copyrighted content.
    """

    __tablename__ = "claim_evidence"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    claim_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    article_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    evidence_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=EvidenceType.ARTICLE_TEXT.value,
    )

    excerpt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_location: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
    )

    anchor_sentence_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    anchor_paragraph_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    anchor_character_start: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    anchor_character_end: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    anchor_content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    strength: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=EvidenceStrength.MODERATE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    claim: Mapped[ClaimModel] = relationship(
        back_populates="evidence_items",
        lazy="selectin",
    )


__all__ = ["ClaimEvidenceModel"]
