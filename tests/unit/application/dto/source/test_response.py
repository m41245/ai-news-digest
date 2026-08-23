"""
Unit tests for SourceResponse DTO.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ai_news_digest.application.dto.source.response import SourceResponse


def test_source_response_with_all_fields() -> None:
    """Test SourceResponse with all fields."""
    response = SourceResponse(
        id="source-123",
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description="Test description",
        is_active=True,
    )

    assert response.id == "source-123"
    assert response.name == "Test Source"
    assert response.feed_url == "https://example.com/feed.xml"
    assert response.website_url == "https://example.com"
    assert response.description == "Test description"
    assert response.is_active is True


def test_source_response_without_website_url() -> None:
    """Test SourceResponse without website_url."""
    response = SourceResponse(
        id="source-123",
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url=None,
        description="Test description",
        is_active=True,
    )

    assert response.website_url is None


def test_source_response_without_description() -> None:
    """Test SourceResponse without description."""
    response = SourceResponse(
        id="source-123",
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url="https://example.com",
        description=None,
        is_active=True,
    )

    assert response.description is None


def test_source_response_inactive() -> None:
    """Test SourceResponse with is_active=False."""
    response = SourceResponse(
        id="source-123",
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url=None,
        description=None,
        is_active=False,
    )

    assert response.is_active is False


def test_source_response_frozen() -> None:
    """Test SourceResponse is frozen."""
    response = SourceResponse(
        id="source-123",
        name="Test Source",
        feed_url="https://example.com/feed.xml",
        website_url=None,
        description=None,
        is_active=True,
    )

    with pytest.raises(FrozenInstanceError):
        response.name = "New Name"
