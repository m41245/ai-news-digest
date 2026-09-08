from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    from ai_news_digest.infrastructure.database.models.article_company_model import (
        ArticleCompanyModel,
    )
    from ai_news_digest.infrastructure.database.models.user_followed_company_model import (
        UserFollowedCompanyModel,
    )
    from ai_news_digest.infrastructure.database.models.user_muted_company_model import (
        UserMutedCompanyModel,
    )


class CompanyModel(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()", onupdate="now()", nullable=False
    )

    article_links: Mapped[list[ArticleCompanyModel]] = relationship(
        back_populates="company", cascade="all, delete-orphan", lazy="selectin"
    )
    followed_by_users: Mapped[list[UserFollowedCompanyModel]] = relationship(
        back_populates="company", lazy="selectin"
    )
    muted_by_users: Mapped[list[UserMutedCompanyModel]] = relationship(
        back_populates="company", lazy="selectin"
    )
