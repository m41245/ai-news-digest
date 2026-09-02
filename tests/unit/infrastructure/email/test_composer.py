"""Unit tests for DigestEmailComposer."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ai_news_digest.domain.enums.digest_format import DigestFormat
from ai_news_digest.domain.models.digest import Digest
from ai_news_digest.infrastructure.email.composer import ComposedEmail, EmailComposer


def _make_digest() -> Digest:
    return Digest.create(
        title="Test Digest",
        content="Para one.\n\nPara two.",
        digest_format=DigestFormat.MARKDOWN,
        article_ids=[],
    )


def test_composer_produces_subject() -> None:
    composer = EmailComposer()
    digest = _make_digest()
    with patch.object(composer, "_render_html", return_value="<html>hi</html>"):
        result = composer.compose(digest)

    assert result.subject == "Test Digest"


def test_composer_produces_html() -> None:
    composer = EmailComposer()
    digest = _make_digest()
    with patch.object(composer, "_render_html", return_value="<html>safe</html>"):
        result = composer.compose(digest)

    assert result.html_body == "<html>safe</html>"


def test_composer_produces_plain_text() -> None:
    composer = EmailComposer()
    digest = _make_digest()
    result = composer.compose(digest)

    assert "Test Digest" in result.text_body
    assert "Para one." in result.text_body
    assert "Para two." in result.text_body


def test_composer_rendered_digest_returns_bytes() -> None:
    composer = EmailComposer()
    digest = _make_digest()
    with patch.object(composer, "_render_html", return_value=b"<html>bytes</html>"):
        result = composer.compose(digest)

    assert result.html_body == b"<html>bytes</html>"


def test_composed_email_is_frozen() -> None:
    email = ComposedEmail(
        subject="s",
        html_body="<html></html>",
        text_body="text",
    )
    with pytest.raises(AttributeError):
        email.subject = "new"  # type: ignore[misc]


def test_composer_does_not_mutate_digest() -> None:
    composer = EmailComposer()
    digest = _make_digest()
    original_content = digest.content
    composer.compose(digest)
    assert digest.content == original_content


def test_composer_plain_text_formatting() -> None:
    composer = EmailComposer()
    digest = _make_digest()
    result = composer.compose(digest)
    lines = result.text_body.splitlines()
    assert lines[0] == "Test Digest"
    assert lines[1] == ""
    assert set(lines[2]) == {"="}


__all__ = [
    "test_composed_email_is_frozen",
    "test_composer_does_not_mutate_digest",
    "test_composer_plain_text_formatting",
    "test_composer_produces_html",
    "test_composer_produces_plain_text",
    "test_composer_produces_subject",
    "test_composer_rendered_digest_returns_bytes",
]
