"""
Unit tests for MarkdownRenderer.
"""

from __future__ import annotations

import pytest

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.infrastructure.rendering.markdown_renderer import MarkdownRenderer


@pytest.fixture
def renderer() -> MarkdownRenderer:
    """Create a MarkdownRenderer instance."""
    return MarkdownRenderer()


@pytest.fixture
def sample_digest() -> Digest:
    """Create a sample Digest."""
    return Digest.create(
        title="Test Digest",
        content="Test content with multiple lines",
        digest_format=DigestFormat.MARKDOWN,
    )


def test_markdown_renderer_format(renderer: MarkdownRenderer) -> None:
    """Test renderer format property."""
    assert renderer.format == DigestFormat.MARKDOWN


def test_markdown_renderer_render_basic(renderer: MarkdownRenderer, sample_digest: Digest) -> None:
    """Test basic markdown rendering."""
    rendered = renderer.render(sample_digest)

    assert rendered.format == DigestFormat.MARKDOWN
    assert "# Test Digest" in rendered.content
    assert "Test content with multiple lines" in rendered.content
    assert "Generated:" in rendered.content


def test_markdown_renderer_render_empty_content(renderer: MarkdownRenderer) -> None:
    """Test rendering digest with empty content."""
    digest = Digest.create(
        title="Empty Digest",
        content="",
        digest_format=DigestFormat.MARKDOWN,
    )

    rendered = renderer.render(digest)

    assert "*No digest content available.*" in rendered.content


def test_markdown_renderer_render_whitespace_content(renderer: MarkdownRenderer) -> None:
    """Test rendering digest with whitespace-only content."""
    digest = Digest.create(
        title="Whitespace Digest",
        content="   ",
        digest_format=DigestFormat.MARKDOWN,
    )

    rendered = renderer.render(digest)

    assert "*No digest content available.*" in rendered.content


def test_markdown_renderer_render_multiline_content(renderer: MarkdownRenderer) -> None:
    """Test rendering digest with multiline content."""
    digest = Digest.create(
        title="Multiline Digest",
        content="Line 1\nLine 2\nLine 3",
        digest_format=DigestFormat.MARKDOWN,
    )

    rendered = renderer.render(digest)

    assert "Line 1" in rendered.content
    assert "Line 2" in rendered.content
    assert "Line 3" in rendered.content


def test_markdown_renderer_render_with_special_chars(renderer: MarkdownRenderer) -> None:
    """Test rendering digest with special characters."""
    digest = Digest.create(
        title="Special <Chars>",
        content="Content with *asterisks* and _underscores_",
        digest_format=DigestFormat.MARKDOWN,
    )

    rendered = renderer.render(digest)

    assert "# Special <Chars>" in rendered.content
    assert "Content with *asterisks* and _underscores_" in rendered.content


def test_markdown_renderer_render_iso_timestamp(
    renderer: MarkdownRenderer, sample_digest: Digest
) -> None:
    """Test that generated timestamp is in readable format."""
    rendered = renderer.render(sample_digest)

    assert "Generated:" in rendered.content
    assert "UTC" in rendered.content
