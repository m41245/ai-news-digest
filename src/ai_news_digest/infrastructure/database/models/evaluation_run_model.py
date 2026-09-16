from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    pass


class EvaluationRunModel(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    evaluation_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    scope: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dataset_version: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="production"
    )
    benchmark_version: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="m93-v1"
    )
    configuration_version: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="v1"
    )
    provider: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    model: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    prompt_version: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    schema_version: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="v1"
    )
    sample_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    metric_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[str | None] = mapped_column(
        "metadata", Text, nullable=True
    )  # type: ignore[misc]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
