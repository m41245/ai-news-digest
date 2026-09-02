"""
Unit tests for rendering module.
"""

from __future__ import annotations

import pytest

from ai_news_digest.application.rendering.renderer import DigestRenderer, RenderedDigest
from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest


def test_rendered_digest_creation() -> None:
    """Test RenderedDigest dataclass creation."""
    digest_format = DigestFormat.MARKDOWN
    content = "# Test Digest"

    rendered = RenderedDigest(
        format=digest_format,
        content=content,
    )

    assert rendered.format == digest_format
    assert rendered.content == content


def test_rendered_digest_frozen() -> None:
    """Test RenderedDigest is frozen."""
    rendered = RenderedDigest(
        format=DigestFormat.MARKDOWN,
        content="# Test",
    )

    with pytest.raises(AttributeError):  # FrozenInstanceError
        rendered.content = "New content"


def test_digest_renderer_abstract() -> None:
    """Test DigestRenderer is abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        DigestRenderer()  # type: ignore[abstract]


def test_concrete_digest_renderer() -> None:
    """Test a concrete DigestRenderer implementation."""

    class TestRenderer(DigestRenderer):
        @property
        def format(self) -> DigestFormat:
            return DigestFormat.MARKDOWN

        def render(self, digest: Digest) -> RenderedDigest:
            return RenderedDigest(
                format=self.format,
                content=f"# {digest.title}",
            )

    digest = Digest.create(
        title="Test Digest",
        content="Test content",
        digest_format=DigestFormat.MARKDOWN,
    )

    renderer = TestRenderer()
    rendered = renderer.render(digest)

    assert rendered.format == DigestFormat.MARKDOWN
    assert rendered.content == "# Test Digest"
    assert renderer.format == DigestFormat.MARKDOWN
