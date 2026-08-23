"""
Unit tests for HTMLRenderer.
"""

from __future__ import annotations

import pytest

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.infrastructure.rendering.html_renderer import HTMLRenderer


@pytest.fixture
def renderer() -> HTMLRenderer:
    """Create an HTMLRenderer instance."""
    return HTMLRenderer()


@pytest.fixture
def sample_digest() -> Digest:
    """Create a sample Digest."""
    return Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.HTML,
    )


def test_html_renderer_format(renderer: HTMLRenderer) -> None:
    """Test renderer format property."""
    assert renderer.format == DigestFormat.HTML


def test_html_renderer_render_basic(renderer: HTMLRenderer, sample_digest: Digest) -> None:
    """Test basic HTML rendering."""
    rendered = renderer.render(sample_digest)

    assert rendered.format == DigestFormat.HTML
    assert "<html" in rendered.content
    assert "</html>" in rendered.content
    assert "<h1>Test Digest</h1>" in rendered.content
    assert "Test content" in rendered.content
    assert "Generated:" in rendered.content


def test_html_renderer_render_html_escaping(renderer: HTMLRenderer) -> None:
    """Test that HTML special characters are escaped."""
    digest = Digest.create(
        title="<script>alert('xss')</script>",
        content="<div>Content</div>",
        digest_format=DigestFormat.HTML,
    )

    rendered = renderer.render(digest)

    assert "&lt;script&gt;" in rendered.content
    assert "&lt;div&gt;" in rendered.content
    assert "<script>" not in rendered.content  # Should be escaped


def test_html_renderer_render_newlines_to_br(renderer: HTMLRenderer) -> None:
    """Test that newlines are converted to paragraph tags."""
    digest = Digest.create(
        title="Line Break Digest",
        content="Line 1\nLine 2\nLine 3",
        digest_format=DigestFormat.HTML,
    )

    rendered = renderer.render(digest)

    assert "<p>" in rendered.content


def test_html_renderer_render_empty_content(renderer: HTMLRenderer) -> None:
    """Test rendering digest with empty content."""
    digest = Digest.create(
        title="Empty Digest",
        content="",
        digest_format=DigestFormat.HTML,
    )

    rendered = renderer.render(digest)

    assert '<div class="content">' in rendered.content


def test_html_renderer_render_iso_timestamp(renderer: HTMLRenderer, sample_digest: Digest) -> None:
    """Test that generated timestamp is in readable format."""
    rendered = renderer.render(sample_digest)

    assert "Generated:" in rendered.content
    assert "UTC" in rendered.content


def test_html_renderer_render_structure(renderer: HTMLRenderer, sample_digest: Digest) -> None:
    """Test that HTML structure is correct."""
    rendered = renderer.render(sample_digest)

    assert "<html" in rendered.content
    assert "<head>" in rendered.content
    assert '<meta charset="UTF-8">' in rendered.content
    assert "<body>" in rendered.content
    assert "</body>" in rendered.content
    assert "</html>" in rendered.content


def test_html_renderer_render_with_special_chars_in_title(renderer: HTMLRenderer) -> None:
    """Test rendering with special characters in title."""
    digest = Digest.create(
        title="Test & Title",
        content="Content",
        digest_format=DigestFormat.HTML,
    )

    rendered = renderer.render(digest)

    assert "Test &amp; Title" in rendered.content
