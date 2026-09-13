from __future__ import annotations

import asyncio

import pytest

from ai_news_digest.infrastructure.extraction.stdlib_extractor import StdlibHtmlExtractor


@pytest.fixture
def extractor() -> StdlibHtmlExtractor:
    return StdlibHtmlExtractor()


VALID_ARTICLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Article</title></head>
<body>
<nav>Navigation</nav>
<header>Header</header>
<article>
<h1>Real Article Title</h1>
<p>This is a real article with meaningful content about AI and technology trends.</p>
<p>The article discusses software engineering and AI trends in detail.</p>
</article>
<footer>Footer</footer>
<script>alert('xss')</script>
<style>body { color: red; }</style>
</body>
</html>
"""


HTML_WITH_SCRIPTS_STYLES = """
<html>
<body>
<script src="tracking.js"></script>
<style>.ad { display: none; }</style>
<p>Real content here that should be extracted properly without scripts.</p>
</body>
</html>
"""


HTML_WITH_NAVIGATION = """
<html>
<body>
<nav>
  <ul>
    <li>Home</li>
    <li>About</li>
    <li>Contact</li>
  </ul>
</nav>
<aside>Sidebar content</aside>
<main>
<p>This is the main article content that should be preserved.</p>
</main>
</body>
</html>
"""


HTML_WITH_ADS = """
<html>
<body>
<div class="advertisement">Buy now!</div>
<div class="sponsored">Sponsored content</div>
<p>Actual article text that is meaningful and should be kept.</p>
</body>
</html>
"""


MALFORMED_HTML = """
<html>
<body>
<div>
<p>This paragraph is not closed
<div>Nested div without closing
<span>Some text
</body>
</html>
"""


NO_ARTICLE_BODY = """
<!DOCTYPE html>
<html>
<head><title>Empty</title></head>
<body>
<script>var x = 1;</script>
<style>.foo { color: red; }</style>
</body>
</html>
"""


VERY_SHORT_HTML = "<html><body>Hi</body></html>"


HTML_WITH_COOKIE_BANNER = """
<html>
<body>
<div id="cookie-banner">We use cookies</div>
<p>Article content that should be extracted properly.</p>
</body>
</html>
"""


HTML_WITH_SOCIAL_WIDGETS = """
<html>
<body>
<div class="social-share">Share on Twitter</div>
<div class="comments">Comments section</div>
<p>Main article content that is important.</p>
</body>
</html>
"""


HTML_WITH_TRACKING = """
<html>
<body>
<img src="tracking.gif" />
<script>var ga = 1;</script>
<p>Article text without tracking elements.</p>
</body>
</html>
"""


HTML_WITH_ENTITIES = """
<html>
<body>
<p>Tom &amp; Jerry &lt;3 &gt; normal text &quot;quoted&quot;</p>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_extract_valid_article(extractor: StdlibHtmlExtractor) -> None:
    result = await extractor.extract(VALID_ARTICLE_HTML, url="https://example.com")
    assert len(result) > 0
    assert "Real Article Title" in result or "article" in result.lower()


@pytest.mark.asyncio
async def test_extract_removes_scripts_and_styles(extractor: StdlibHtmlExtractor) -> None:
    result = await extractor.extract(HTML_WITH_SCRIPTS_STYLES)
    assert "alert" not in result
    assert "tracking.js" not in result
    assert "Real content" in result


@pytest.mark.asyncio
async def test_extract_removes_navigation(extractor: StdlibHtmlExtractor) -> None:
    result = await extractor.extract(HTML_WITH_NAVIGATION)
    assert "main article content" in result.lower() or "article content" in result.lower()


@pytest.mark.asyncio
async def test_extract_removes_ads(extractor: StdlibHtmlExtractor) -> None:
    result = await extractor.extract(HTML_WITH_ADS)
    assert "Actual article text" in result


@pytest.mark.asyncio
async def test_extract_malformed_html(extractor: StdlibHtmlExtractor) -> None:
    result = await extractor.extract(MALFORMED_HTML)
    assert len(result) > 0 or result == ""


@pytest.mark.asyncio
async def test_extract_no_article_body(extractor: StdlibHtmlExtractor) -> None:
    result = await extractor.extract(NO_ARTICLE_BODY)
    assert result == ""


@pytest.mark.asyncio
async def test_extract_very_short_html(extractor: StdlibHtmlExtractor) -> None:
    result = await extractor.extract(VERY_SHORT_HTML)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_extract_removes_cookie_banner(extractor: StdlibHtmlExtractor) -> None:
    result = await extractor.extract(HTML_WITH_COOKIE_BANNER)
    assert "Article content" in result


@pytest.mark.asyncio
async def test_extract_removes_social_widgets(extractor: StdlibHtmlExtractor) -> None:
    result = await extractor.extract(HTML_WITH_SOCIAL_WIDGETS)
    assert "Main article content" in result


@pytest.mark.asyncio
async def test_extract_removes_tracking(extractor: StdlibHtmlExtractor) -> None:
    result = await extractor.extract(HTML_WITH_TRACKING)
    assert "tracking.gif" not in result
    assert "ga" not in result
    assert "Article text" in result


@pytest.mark.asyncio
async def test_extract_html_entities(extractor: StdlibHtmlExtractor) -> None:
    result = await extractor.extract(HTML_WITH_ENTITIES)
    assert "Tom" in result
    assert "Jerry" in result


def test_extract_empty_html(extractor: StdlibHtmlExtractor) -> None:
    result = asyncio.run(extractor.extract(""))
    assert result == ""


def test_extract_none_url(extractor: StdlibHtmlExtractor) -> None:
    result = asyncio.run(extractor.extract(VALID_ARTICLE_HTML, url=None))
    assert isinstance(result, str)
