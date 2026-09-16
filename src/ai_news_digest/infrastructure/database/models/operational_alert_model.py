from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ai_news_digest.infrastructure.database.base import Base

if TYPE_CHECKING:
    pass


class OperationalAlertModel(Base):
    __tablename__ = "operational_alerts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    alert_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=True, index=True
    )
    severity: Mapped[str] = mapped_column(
        String(16), nullable=False, index=True
    )
    component: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    gate_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
    message: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    details: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    resolved: Mapped[bool] = mapped_column(
        Integer, nullable=False, server_default="0", index=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deduplication_key: Mapped[str] = mapped_column(
        String(256), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
