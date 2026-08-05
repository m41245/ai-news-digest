"""
RSS client exceptions.
"""

from __future__ import annotations


class RSSException(Exception):
    """Base exception for RSS-related failures."""


class RSSClientError(RSSException):
    """Base exception for RSS client."""


class RSSConnectionError(RSSClientError):
    """Raised when a feed cannot be reached."""


class RSSRequestError(RSSClientError):
    """Raised when an HTTP request fails."""


class RSSInvalidResponseError(RSSClientError):
    """Raised when the response is invalid."""


class RSSTimeoutError(RSSClientError):
    """Raised when the request times out."""
