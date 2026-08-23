"""
Unit tests for the CanonicalUrl value object.
"""

from __future__ import annotations

from ai_news_digest.domain.models.url import CanonicalUrl


class TestCanonicalUrlFragments:
    """Fragments must be removed."""

    def test_fragment_stripped(self) -> None:
        result = CanonicalUrl.parse("https://example.com/article#section-1")

        assert result.value == "https://example.com/article"

    def test_fragment_with_tracking_stripped(self) -> None:
        result = CanonicalUrl.parse("https://example.com/article?utm_source=x#top")

        assert result.value == "https://example.com/article"

    def test_empty_fragment(self) -> None:
        result = CanonicalUrl.parse("https://example.com/article#")

        assert result.value == "https://example.com/article"


class TestCanonicalUrlTrackingParams:
    """Known tracking query parameters must be removed."""

    def test_utm_source_removed(self) -> None:
        result = CanonicalUrl.parse("https://example.com/article?utm_source=newsletter")

        assert result.value == "https://example.com/article"

    def test_multiple_utm_removed(self) -> None:
        result = CanonicalUrl.parse(
            "https://example.com/article?utm_source=a&utm_medium=b&utm_campaign=c"
        )

        assert result.value == "https://example.com/article"

    def test_fbclid_removed(self) -> None:
        result = CanonicalUrl.parse("https://example.com/article?fbclid=abc123")

        assert result.value == "https://example.com/article"

    def test_gclid_removed(self) -> None:
        result = CanonicalUrl.parse("https://example.com/article?gclid=xyz")

        assert result.value == "https://example.com/article"

    def test_mixed_tracking_and_real_params(self) -> None:
        result = CanonicalUrl.parse("https://example.com/article?id=42&utm_source=email&page=2")

        assert "utm_source" not in result.value
        assert "id=42" in result.value
        assert "page=2" in result.value


class TestCanonicalUrlPreservesLegitParams:
    """Non-tracking query parameters must be preserved."""

    def test_pagination_preserved(self) -> None:
        result = CanonicalUrl.parse("https://example.com/blog?page=3")

        assert result.value == "https://example.com/blog?page=3"

    def test_search_query_preserved(self) -> None:
        result = CanonicalUrl.parse("https://example.com/search?q=ai&lang=en")

        assert "q=ai" in result.value
        assert "lang=en" in result.value

    def test_empty_query_removed(self) -> None:
        result = CanonicalUrl.parse("https://example.com/article?")

        assert result.value == "https://example.com/article"


class TestCanonicalUrlCaseNormalization:
    """Scheme and host are lowercased."""

    def test_scheme_lowercased(self) -> None:
        result = CanonicalUrl.parse("HTTPS://Example.COM/Article")

        assert result.value.startswith("https://")

    def test_host_lowercased(self) -> None:
        result = CanonicalUrl.parse("https://Example.COM/article")

        assert "example.com" in result.value

    def test_path_preserved_case(self) -> None:
        result = CanonicalUrl.parse("https://example.com/My/Article")

        assert "/My/Article" in result.value


class TestCanonicalUrlDefaultPorts:
    """Default HTTP/HTTPS ports are stripped."""

    def test_http_default_port_stripped(self) -> None:
        result = CanonicalUrl.parse("http://example.com:80/article")

        assert ":80" not in result.value

    def test_https_default_port_stripped(self) -> None:
        result = CanonicalUrl.parse("https://example.com:443/article")

        assert ":443" not in result.value

    def test_non_default_port_preserved(self) -> None:
        result = CanonicalUrl.parse("http://example.com:8080/article")

        assert ":8080" in result.value


class TestCanonicalUrlPathNormalization:
    """Paths are normalized for '.'/'..' and duplicate slashes."""

    def test_dot_segments_removed(self) -> None:
        result = CanonicalUrl.parse("https://example.com/a/./b")

        assert result.value == "https://example.com/a/b"

    def test_dotdot_segments_collapse(self) -> None:
        result = CanonicalUrl.parse("https://example.com/a/b/../c")

        assert result.value == "https://example.com/a/c"

    def test_trailing_slash_preserved(self) -> None:
        result = CanonicalUrl.parse("https://example.com/path/")

        assert result.value == "https://example.com/path/"

    def test_root_path_preserved(self) -> None:
        result = CanonicalUrl.parse("https://example.com/")

        assert result.value == "https://example.com/"


class TestCanonicalUrlStability:
    """Canonicalization is idempotent and deterministic."""

    def test_idempotent(self) -> None:
        url = "https://example.com/article?id=1&utm_source=x#frag"
        first = CanonicalUrl.parse(url)
        second = CanonicalUrl.parse(first.value)

        assert first.value == second.value

    def test_deterministic_across_calls(self) -> None:
        url = "http://Example.COM:80/A?utm_source=1&B=2"
        first = CanonicalUrl.parse(url)
        second = CanonicalUrl.parse(url)

        assert first.value == second.value

    def test_different_inputs_canonicalize_same(self) -> None:
        a = CanonicalUrl.parse("https://example.com/article?utm_source=fb")
        b = CanonicalUrl.parse("https://example.com/article#readme")

        assert a.value == b.value == "https://example.com/article"


class TestCanonicalUrlMalformed:
    """Malformed URLs are handled gracefully."""

    def test_empty_string(self) -> None:
        result = CanonicalUrl.parse("")

        assert result.value == ""

    def test_whitespace_only(self) -> None:
        result = CanonicalUrl.parse("   ")

        assert result.value == ""

    def test_whitespace_stripped(self) -> None:
        result = CanonicalUrl.parse("  https://example.com/a  ")

        assert result.value == "https://example.com/a"

    def test_url_with_spaces_in_path(self) -> None:
        result = CanonicalUrl.parse("https://example.com/my article")

        assert "example.com" in result.value

    def test_partial_url_no_scheme(self) -> None:
        """A scheme-less URL is still returned as-is (best-effort)."""
        result = CanonicalUrl.parse("example.com/article")

        # urlparse treats this as path; we do not invent a scheme.
        assert result.value == "example.com/article"


class TestCanonicalUrlFrozenValueObject:
    """CanonicalUrl is an immutable value object."""

    def test_case_normalizes_scheme_and_host(self) -> None:
        """Scheme and host are lowercased; path case is preserved."""
        a = CanonicalUrl.parse("HTTPS://EXAMPLE.COM/a")
        b = CanonicalUrl.parse("https://example.com/a")

        assert a == b

    def test_path_case_sensitive(self) -> None:
        """Path case is preserved; different paths are not equal."""
        a = CanonicalUrl.parse("https://example.com/a")
        b = CanonicalUrl.parse("https://example.com/A")

        assert a != b

    def test_hashable(self) -> None:
        a = CanonicalUrl.parse("https://example.com/a")
        b = CanonicalUrl.parse("https://example.com/a")

        assert hash(a) == hash(b)
        assert {a, b} == {a}
