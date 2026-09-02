"""
Unit tests for UpdateSourceRequest DTO.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from ai_news_digest.application.dto.source.update_request import UpdateSourceRequest


def test_update_source_request_with_all_fields() -> None:
    """Test UpdateSourceRequest with all fields."""
    source_id = uuid4()
    request = UpdateSourceRequest(
        id=source_id,
        name="Updated Name",
        feed_url="https://updated.com/feed.xml",
        website_url="https://updated.com",
        description="Updated description",
        is_active=False,
    )

    assert request.id == source_id
    assert request.name == "Updated Name"
    assert request.feed_url == "https://updated.com/feed.xml"
    assert request.website_url == "https://updated.com"
    assert request.description == "Updated description"
    assert request.is_active is False


def test_update_source_request_with_id_only() -> None:
    """Test UpdateSourceRequest with only id field."""
    source_id = uuid4()
    request = UpdateSourceRequest(id=source_id)

    assert request.id == source_id
    assert request.name is None
    assert request.feed_url is None
    assert request.website_url is None
    assert request.description is None
    assert request.is_active is None


def test_update_source_request_with_partial_fields() -> None:
    """Test UpdateSourceRequest with partial fields."""
    source_id = uuid4()
    request = UpdateSourceRequest(
        id=source_id,
        name="Updated Name",
        is_active=False,
    )

    assert request.id == source_id
    assert request.name == "Updated Name"
    assert request.feed_url is None
    assert request.website_url is None
    assert request.description is None
    assert request.is_active is False


def test_update_source_request_frozen() -> None:
    """Test UpdateSourceRequest is frozen."""
    source_id = uuid4()
    request = UpdateSourceRequest(id=source_id)

    with pytest.raises(FrozenInstanceError):
        request.name = "New Name"
