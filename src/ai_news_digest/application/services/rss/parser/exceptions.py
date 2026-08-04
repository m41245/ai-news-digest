from __future__ import annotations


class RSSParserError(Exception):
    """
    Base exception raised by the RSS parser.
    """


class RSSParsingError(RSSParserError):
    """
    Raised when XML parsing fails.
    """


class RSSFeedFormatError(RSSParserError):
    """
    Raised when the feed is neither RSS nor Atom.
    """


class RSSArticleValidationError(RSSParserError):
    """
    Raised when an article is missing required fields.
    """
