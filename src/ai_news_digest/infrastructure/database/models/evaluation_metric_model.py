from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    pass


class EvaluationMetricModel(Base):
    __tablename__ = "evaluation_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    sample_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    scope: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    provider: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    schema_version: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="v1"
    )
    dataset_version: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="production"
    )
    benchmark_version: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="m93-v1"
    )
    extra_metadata: Mapped[str | None] = mapped_column(
        "metadata", Text, nullable=True
    )  # type: ignore[misc]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
