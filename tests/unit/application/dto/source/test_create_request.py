"""
Unit tests for CreateSourceRequest DTO.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ai_news_digest.application.dto.source.create_request import CreateSourceRequest


def test_create_source_request_with_all_fields() -> None:
    """Test CreateSourceRequest with all fields."""
    request = CreateSourceRequest(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
        is_active=True,
    )

    assert request.name == "Test Source"
    assert request.feed_url == "https://example.com/feed.xml"
    assert request.website_url == "https://example.com"
    assert request.description == "Test description"
    assert request.is_active is True


def test_create_source_request_with_required_fields_only() -> None:
    """Test CreateSourceRequest with only required fields."""
    request = CreateSourceRequest(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )

    assert request.name == "Test Source"
    assert request.feed_url == "https://example.com/feed.xml"
    assert request.website_url is None
    assert request.description is None
    assert request.is_active is True  # Default value


def test_create_source_request_inactive() -> None:
    """Test CreateSourceRequest with is_active=False."""
    request = CreateSourceRequest(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        is_active=False,
    )

    assert request.is_active is False


def test_create_source_request_frozen() -> None:
    """Test CreateSourceRequest is frozen."""
    request = CreateSourceRequest(
        name="Test Source",
        feed_url="https://example.com/feed.xml",
    )

    with pytest.raises(FrozenInstanceError):
        request.name = "New Name"
