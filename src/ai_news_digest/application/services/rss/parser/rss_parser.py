from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element

from defusedxml import ElementTree

from .exceptions import (
    RSSArticleValidationError,
    RSSFeedFormatError,
    RSSParsingError,
)
from .models import ParsedArticle


class RSSParser:
    """
    Parses RSS 2.0 and Atom feeds into ParsedArticle objects.
    """

    def parse(self, xml: str) -> list[ParsedArticle]:
        """
        Parse an RSS or Atom feed.
        """

        try:
            root = ElementTree.fromstring(xml)
        except ElementTree.ParseError as exc:
            raise RSSParsingError("Invalid XML document.") from exc

        tag = self._strip_namespace(root.tag)

        if tag == "rss":
            return self._parse_rss(root)

        if tag == "feed":
            return self._parse_atom(root)

        raise RSSFeedFormatError("Unsupported feed format.")

    def _parse_rss(
        self,
        root: Element,
    ) -> list[ParsedArticle]:
        channel = root.find("channel")

        if channel is None:
            raise RSSFeedFormatError("RSS channel not found.")

        articles: list[ParsedArticle] = []

        for item in channel.findall("item"):
            articles.append(self._parse_rss_item(item))

        return articles

    def _parse_atom(
        self,
        root: Element,
    ) -> list[ParsedArticle]:
        namespace = self._namespace(root.tag)

        articles: list[ParsedArticle] = []

        for entry in root.findall(f"{namespace}entry"):
            articles.append(self._parse_atom_entry(entry, namespace))

        return articles

    def _parse_rss_item(
        self,
        item: Element,
    ) -> ParsedArticle:
        title = self._required_text(item.find("title"), "title")
        link = self._required_text(item.find("link"), "link")

        summary = item.findtext("description") or ""

        published = self._parse_date(
            item.findtext("pubDate"),
        )

        return ParsedArticle(
            title=title,
            url=link,
            summary=summary,
            published_at=published,
        )

    def _parse_atom_entry(
        self,
        entry: Element,
        namespace: str,
    ) -> ParsedArticle:
        title = self._required_text(
            entry.find(f"{namespace}title"),
            "title",
        )

        link_element = entry.find(f"{namespace}link")

        if (
            link_element is None
            or "href" not in link_element.attrib
        ):
            raise RSSArticleValidationError(
                "Atom entry missing link.",
            )

        summary = (
            entry.findtext(f"{namespace}summary")
            or ""
        )

        published = self._parse_date(
            entry.findtext(f"{namespace}updated")
            or entry.findtext(f"{namespace}published"),
        )

        return ParsedArticle(
            title=title,
            url=link_element.attrib["href"],
            summary=summary,
            published_at=published,
        )

    @staticmethod
    def _required_text(
        element: Element | None,
        field: str,
    ) -> str:
        if element is None or not element.text:
            raise RSSArticleValidationError(
                f"Missing required field: {field}",
            )

        return element.text.strip()

    @staticmethod
    def _parse_date(value: str | None) -> datetime:
        if not value:
            return datetime.now(UTC)

        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return datetime.now(UTC)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)

        return dt.astimezone(UTC)

    @staticmethod
    def _strip_namespace(tag: str) -> str:
        return str(tag.split("}", 1)[-1])

    @staticmethod
    def _namespace(tag: str) -> str:
        if tag.startswith("{"):
            return str(tag.split("}", 1)[0] + "}")

        return ""
