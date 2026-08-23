from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    from ai_news_digest.infrastructure.database.models.article_model import (
        ArticleModel,
    )
    from ai_news_digest.infrastructure.database.models.digest_model import (
        DigestModel,
    )


class DigestArticleModel(Base):
    """
    Association table linking digests and articles.

    This association object allows storing metadata about
    each article's inclusion in a digest, such as ordering
    and future scoring information.
    """

    __tablename__ = "digest_articles"

    __table_args__ = (
        UniqueConstraint(
            "digest_id",
            "article_id",
            name="uq_digest_article",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    digest_id: Mapped[str] = mapped_column(
        ForeignKey("digests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    article_id: Mapped[str] = mapped_column(
        ForeignKey("articles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    digest: Mapped[DigestModel] = relationship(
        back_populates="digest_articles",
        lazy="selectin",
    )

    article: Mapped[ArticleModel] = relationship(
        back_populates="digest_articles",
        lazy="selectin",
    )
