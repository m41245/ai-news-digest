from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    pass


class ComponentHealthSnapshotModel(Base):
    __tablename__ = "component_health_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    snapshot_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    component: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )
    metric_type: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    metric_value: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    sample_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    baseline_value: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    drift_state: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    evaluation_run_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    configuration_version: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="v1"
    )
    warnings: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
