from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_news_digest.domain.enums.article_status import ArticleStatus
from ai_news_digest.domain.enums.extraction_method import ExtractionMethod
from ai_news_digest.domain.enums.extraction_quality import ExtractionQuality
from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    from ai_news_digest.infrastructure.database.models.article_category_model import (
        ArticleCategoryModel,
    )
    from ai_news_digest.infrastructure.database.models.article_company_model import (
        ArticleCompanyModel,
    )
    from ai_news_digest.infrastructure.database.models.article_topic_model import (
        ArticleTopicModel,
    )
    from ai_news_digest.infrastructure.database.models.category_model import (
        CategoryModel,
    )
    from ai_news_digest.infrastructure.database.models.digest_article_model import (
        DigestArticleModel,
    )
    from ai_news_digest.infrastructure.database.models.source_model import (
        SourceModel,
    )
    from ai_news_digest.infrastructure.database.models.story_cluster_model import (
        StoryClusterModel,
    )


class ArticleModel(Base):
    """
    Database representation of a news article.
    """

    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    source_id: Mapped[str] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category_id: Mapped[str | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        unique=True,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[ArticleStatus] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Extraction pipeline metadata.
    extraction_method: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=ExtractionMethod.RSS.value,
    )
    extraction_quality: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=ExtractionQuality.NONE.value,
    )
    extracted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    content_char_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Structured AI intelligence.
    importance_score: Mapped[float | None] = mapped_column(
        nullable=True,
    )
    confidence: Mapped[float | None] = mapped_column(
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
    ai_processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    key_takeaways_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    why_it_matters: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    topics_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source: Mapped[SourceModel] = relationship(
        back_populates="articles",
        lazy="selectin",
    )

    category: Mapped[CategoryModel | None] = relationship(
        back_populates="articles",
        lazy="selectin",
    )

    digest_articles: Mapped[list[DigestArticleModel]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    company_links: Mapped[list[ArticleCompanyModel]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    topic_links: Mapped[list[ArticleTopicModel]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    category_links: Mapped[list[ArticleCategoryModel]] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    cluster_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("story_clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    cluster: Mapped[StoryClusterModel | None] = relationship(
        back_populates="articles",
        lazy="selectin",
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
