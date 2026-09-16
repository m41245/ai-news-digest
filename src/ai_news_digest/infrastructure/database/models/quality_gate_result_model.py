from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    pass


class QualityGateResultModel(Base):
    __tablename__ = "quality_gate_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    gate_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    component: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    metric_type: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    result: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    current_value: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    threshold: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    operator: Mapped[str] = mapped_column(
        String(16), nullable=False
    )
    sample_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    min_sample_size: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False
    )
    explanation: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    evaluation_run_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    configuration_version: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="v1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
