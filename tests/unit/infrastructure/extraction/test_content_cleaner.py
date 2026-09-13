from __future__ import annotations

import pytest

from ai_news_digest.infrastructure.extraction.content_cleaner import ContentCleaner


@pytest.fixture
def cleaner() -> ContentCleaner:
    return ContentCleaner()


def test_clean_none_input(cleaner: ContentCleaner) -> None:
    assert cleaner.clean(None) == ""


def test_clean_empty_string(cleaner: ContentCleaner) -> None:
    assert cleaner.clean("") == ""


def test_clean_whitespace_normalization(cleaner: ContentCleaner) -> None:
    result = cleaner.clean("word1    word2 with more text here now")
    assert "word1" in result
    assert "word2" in result
    assert "    " not in result


def test_clean_tab_normalization(cleaner: ContentCleaner) -> None:
    result = cleaner.clean("word1\t\tword2 with more text here now")
    assert "\t\t" not in result
    assert "word1" in result
    assert "word2" in result


def test_clean_line_ending_normalization(cleaner: ContentCleaner) -> None:
    result = cleaner.clean("line1 with text\r\nline2 with text\rline3 with text")
    assert "\r\n" not in result
    assert "\r" not in result
    assert "line1" in result
    assert "line2" in result
    assert "line3" in result


def test_clean_repeated_blank_lines_collapsed(cleaner: ContentCleaner) -> None:
    result = cleaner.clean("para1 with text\n\n\n\n\npara2 with text")
    assert "\n\n\n" not in result
    assert "para1" in result
    assert "para2" in result


def test_clean_short_paragraph_removal(cleaner: ContentCleaner) -> None:
    input_text = "Short\n\nThis is a meaningful paragraph with enough words.\n\nX"
    result = cleaner.clean(input_text)
    assert "Short" not in result
    assert "X" not in result
    assert "meaningful paragraph" in result


def test_clean_html_entity_decoding(cleaner: ContentCleaner) -> None:
    result = cleaner.clean("Tom &amp; Jerry &lt;3")
    assert "Tom & Jerry" in result
    assert "<3" in result


def test_clean_malformed_markup(cleaner: ContentCleaner) -> None:
    result = cleaner.clean("<div>Some text here in detail</span>")
    assert isinstance(result, str)
    assert "Some text here in detail" in result


def test_clean_meaningful_content_preserved(cleaner: ContentCleaner) -> None:
    text = "First paragraph with enough words.\n\nSecond paragraph also with enough words."
    result = cleaner.clean(text)
    assert "First paragraph" in result
    assert "Second paragraph" in result


def test_clean_only_short_content_preserved(cleaner: ContentCleaner) -> None:
    text = "Hi"
    result = cleaner.clean(text)
    assert result == "Hi"
