"""Unit tests for DeliveryStatus enum."""

from __future__ import annotations

import pytest

from ai_news_digest.domain.enums.delivery_status import DeliveryStatus


def test_delivery_status_values() -> None:
    assert DeliveryStatus.PENDING.value == "pending"
    assert DeliveryStatus.SENT.value == "sent"
    assert DeliveryStatus.FAILED.value == "failed"


def test_delivery_status_members() -> None:
    assert set(DeliveryStatus) == {
        DeliveryStatus.PENDING,
        DeliveryStatus.SENT,
        DeliveryStatus.FAILED,
    }


def test_delivery_status_from_string() -> None:
    assert DeliveryStatus("pending") is DeliveryStatus.PENDING
    assert DeliveryStatus("sent") is DeliveryStatus.SENT
    assert DeliveryStatus("failed") is DeliveryStatus.FAILED


def test_delivery_status_invalid_string() -> None:
    with pytest.raises(ValueError):
        DeliveryStatus("invalid")


__all__ = [
    "test_delivery_status_from_string",
    "test_delivery_status_invalid_string",
    "test_delivery_status_members",
    "test_delivery_status_values",
]
