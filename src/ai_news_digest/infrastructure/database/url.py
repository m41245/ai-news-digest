"""Translate PostgreSQL/libpq URLs to SQLAlchemy's asyncpg dialect.

Neon supplies a standard libpq connection URL. SQLAlchemy's asyncpg dialect
does not pass that URL to asyncpg as a DSN; it copies URL query parameters
directly into ``asyncpg.connect()`` instead. Consequently, libpq-only
parameters such as ``sslmode`` and ``channel_binding`` would otherwise become
unexpected Python keyword arguments.

This module is the single boundary for application engines and Alembic:

* PostgreSQL URLs are changed to the ``postgresql+asyncpg`` dialect.
* Parameters accepted by the installed asyncpg API (plus SQLAlchemy's
  asyncpg-dialect parameters) remain in the URL.
* ``sslmode`` is translated to the asyncpg-native ``ssl`` connect argument.
* ``application_name`` is translated to asyncpg ``server_settings``.
* ``channel_binding`` is consumed because asyncpg 0.31 does not expose a
  channel-binding argument. ``channel_binding=require`` still forces TLS; the
  limitation is documented rather than pretending asyncpg enforces the libpq
  channel-binding requirement.
* Other unsupported parameters are consumed so they cannot leak into
  ``asyncpg.connect()``. Unsupported TLS certificate parameters fail closed,
  because silently dropping them could weaken certificate validation.
"""

from __future__ import annotations

import inspect
from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import asyncpg  # type: ignore[import-untyped]

type AsyncpgConnectArgs = dict[str, bool | str | dict[str, str]]

_POSTGRES_SCHEMES = frozenset({"postgresql", "postgresql+asyncpg"})

# SQLAlchemy removes these from the kwargs before calling asyncpg.connect().
# They are valid URL options for the asyncpg dialect, but are not asyncpg
# connection keywords themselves.
_SQLALCHEMY_ASYNCPG_PARAMETERS = frozenset(
    {
        "async_fallback",
        "prepared_statement_cache_size",
        "prepared_statement_name_func",
    }
)

# These asyncpg parameters are Python objects or are otherwise not meaningful
# as URL query-string values. The remaining signature parameters are safe to
# preserve in the URL and SQLAlchemy will pass them to asyncpg.
_NON_URL_ASYNCPG_PARAMETERS = frozenset(
    {"connection_class", "dsn", "loop", "record_class", "server_settings"}
)
_ASYNCPG_URL_PARAMETERS = frozenset(inspect.signature(asyncpg.connect).parameters)
_ASYNCPG_URL_PARAMETERS -= _NON_URL_ASYNCPG_PARAMETERS
_ALLOWED_URL_PARAMETERS = _ASYNCPG_URL_PARAMETERS | _SQLALCHEMY_ASYNCPG_PARAMETERS

_SSLMODE_TLS_VALUES = frozenset({"require", "verify-ca", "verify-full"})
_SSLMODE_OPTIONAL_VALUES = frozenset({"allow", "prefer"})
_SSLMODE_VALUES = _SSLMODE_TLS_VALUES | _SSLMODE_OPTIONAL_VALUES | {"disable"}
_CHANNEL_BINDING_VALUES = frozenset({"disable", "prefer", "require"})

# asyncpg's direct connect API cannot consume these libpq TLS-file options.
# Raising for them is safer than dropping them and accidentally changing the
# requested certificate or client-authentication semantics.
_UNSUPPORTED_TLS_PARAMETERS = frozenset(
    {
        "sslcert",
        "sslcrl",
        "sslkey",
        "sslpassword",
        "sslrootcert",
        "ssl_max_protocol_version",
        "ssl_min_protocol_version",
        "sslnegotiation",
    }
)


def _parse_postgresql_query(url: str) -> list[tuple[str, str]]:
    return parse_qsl(urlparse(url).query, keep_blank_values=True)


def _last_query_value(query: Iterable[tuple[str, str]], name: str) -> str | None:
    values = [value for key, value in query if key == name]
    return values[-1] if values else None


def _validate_query_parameters(query: Iterable[tuple[str, str]]) -> None:
    for key, _ in query:
        if key in _UNSUPPORTED_TLS_PARAMETERS:
            raise ValueError(
                f"DATABASE_URL contains unsupported asyncpg TLS parameter {key!r}; "
                "provide asyncpg-compatible SSL settings instead"
            )

    sslmode = _last_query_value(query, "sslmode")
    if sslmode is not None and sslmode not in _SSLMODE_VALUES:
        raise ValueError(
            f"DATABASE_URL contains unsupported sslmode={sslmode!r}; "
            f"expected one of {sorted(_SSLMODE_VALUES)}"
        )

    channel_binding = _last_query_value(query, "channel_binding")
    if channel_binding is not None and channel_binding not in _CHANNEL_BINDING_VALUES:
        raise ValueError(
            f"DATABASE_URL contains unsupported channel_binding={channel_binding!r}; "
            f"expected one of {sorted(_CHANNEL_BINDING_VALUES)}"
        )


def _normalized_query(query: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    """Keep only query keys that SQLAlchemy/asyncpg can consume safely."""
    return [(key, value) for key, value in query if key in _ALLOWED_URL_PARAMETERS]


def normalize_database_url(url: str) -> str:
    """Return a URL safe to give to SQLAlchemy's asyncpg dialect.

    The helper intentionally filters query parameters using the installed
    asyncpg ``connect`` signature instead of dropping every query parameter.
    Supported asyncpg options and SQLAlchemy dialect options remain intact;
    libpq-only options are consumed or translated by
    :func:`get_asyncpg_connect_args`.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _POSTGRES_SCHEMES:
        return url

    query = _parse_postgresql_query(url)
    _validate_query_parameters(query)

    if parsed.scheme == "postgresql":
        parsed = parsed._replace(scheme="postgresql+asyncpg")

    new_query = urlencode(_normalized_query(query), doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def get_asyncpg_connect_args(url: str) -> AsyncpgConnectArgs:
    """Return asyncpg-native connection arguments derived from *url*.

    ``sslmode=require`` and the two certificate-verifying modes use
    ``ssl=True``. In asyncpg 0.31 this creates a default TLS client context,
    including certificate and hostname verification, so ``require`` is not
    downgraded to plaintext or an unverified connection. ``sslmode=disable``
    maps explicitly to ``ssl=False`` for local/non-TLS development.

    asyncpg 0.31 has no ``channel_binding`` argument. For Neon URLs,
    ``channel_binding=require`` is consumed and TLS is forced if necessary;
    asyncpg cannot enforce the additional SCRAM channel-binding requirement.
    This is intentionally explicit so the application does not claim a
    security guarantee its driver does not provide.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _POSTGRES_SCHEMES:
        return {}

    query = parse_qsl(parsed.query, keep_blank_values=True)
    _validate_query_parameters(query)

    connect_args: AsyncpgConnectArgs = {}
    sslmode = _last_query_value(query, "sslmode")
    channel_binding = _last_query_value(query, "channel_binding")

    if sslmode in _SSLMODE_TLS_VALUES:
        # True uses asyncpg's secure default SSLContext, unlike sslmode=require
        # passed as a string which intentionally permits unverified TLS.
        connect_args["ssl"] = True
    elif sslmode == "disable":
        connect_args["ssl"] = False
    elif sslmode in _SSLMODE_OPTIONAL_VALUES:
        # asyncpg accepts these SSL mode strings natively through its ``ssl``
        # argument and preserves libpq's allow/prefer negotiation behavior.
        connect_args["ssl"] = sslmode

    if channel_binding == "require":
        if sslmode == "disable":
            raise ValueError("channel_binding=require cannot be used with sslmode=disable")
        # Channel binding requires TLS. asyncpg does not expose the libpq
        # channel_binding switch, so enforce the part asyncpg can guarantee.
        connect_args["ssl"] = True

    application_name = _last_query_value(query, "application_name")
    if application_name is not None:
        connect_args["server_settings"] = {"application_name": application_name}

    return connect_args


def get_asyncpg_engine_kwargs(url: str) -> tuple[str, AsyncpgConnectArgs]:
    """Return the normalized URL and matching ``connect_args`` pair."""
    return normalize_database_url(url), get_asyncpg_connect_args(url)
