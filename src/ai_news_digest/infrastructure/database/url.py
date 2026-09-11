"""Shared database URL normalization for PostgreSQL + asyncpg compatibility.

Standard Neon/PostgreSQL connection strings may include ``sslmode=require`` as a
query parameter. The ``asyncpg`` driver does not accept ``sslmode`` as a
connection keyword argument; instead TLS is enabled by passing ``ssl=True`` via
``connect_args``.

This module provides a single source of truth for:

1. Normalizing ``postgresql://`` to ``postgresql+asyncpg://``.
2. Consuming ``sslmode=require`` (and similar TLS-enabling modes) from the URL
   query string so asyncpg never receives it as an unknown keyword argument.
3. Returning the equivalent ``connect_args`` to enable TLS via asyncpg-native
   parameters.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def normalize_database_url(url: str) -> str:
    """Normalize a PostgreSQL URL for use with the asyncpg dialect.

    Steps:

    1. Convert ``postgresql://`` scheme to ``postgresql+asyncpg://`` when the
       caller has not already specified a dialect.
    2. Remove the ``sslmode`` query parameter so asyncpg never sees it as an
       unexpected connection keyword argument.
    3. Preserve all other query parameters unchanged.

    Non-PostgreSQL URLs (SQLite, etc.) are returned unchanged.
    """
    if not url.startswith("postgresql://") and not url.startswith(
        "postgresql+asyncpg://"
    ):
        return url

    parsed = urlparse(url)

    if parsed.scheme == "postgresql":
        parsed = parsed._replace(scheme="postgresql+asyncpg")

    query = parse_qs(parsed.query, keep_blank_values=True)
    query.pop("sslmode", None)

    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


_SSLMODE_TLS_VALUES = frozenset({"require", "verify-ca", "verify-full"})


def get_asyncpg_connect_args(url: str) -> dict[str, bool | dict[str, str]]:
    """Return asyncpg ``connect_args`` derived from *url*.

    Currently:

    - When *url* uses the asyncpg dialect and its query string contained
      ``sslmode=require`` (or another TLS-enforcing mode), ``{"ssl": True}``
      is returned so asyncpg negotiates TLS.
    - When *url* is a plain ``postgresql://`` URL with ``sslmode=require``,
      ``{"ssl": True}`` is also returned (the URL will be normalized
      separately before being passed to the engine).
    - Otherwise an empty dict is returned (caller can merge with other args).
    """
    is_postgres = url.startswith("postgresql://") or url.startswith(
        "postgresql+asyncpg://"
    )
    if not is_postgres:
        return {}

    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)

    sslmode_values = query.get("sslmode", [])
    if any(value in _SSLMODE_TLS_VALUES for value in sslmode_values):
        return {"ssl": True}

    return {}


def get_asyncpg_engine_kwargs(url: str) -> tuple[str, dict[str, bool | dict[str, str]]]:
    """Return a ``(normalized_url, connect_args)`` pair for engine creation.

    This is the preferred single-call entry-point when both the URL and
    ``connect_args`` are needed (e.g., in SQLAlchemy engine setup).
    """
    normalized = normalize_database_url(url)
    connect_args = get_asyncpg_connect_args(url)
    return normalized, connect_args
