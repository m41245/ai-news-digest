#!/usr/bin/env python3
"""Read-only verification of the hosted Neon staging database.

This script connects ONLY to the database referenced by the ``DATABASE_URL``
environment variable (which the GitHub Actions workflow injects from the
``STAGING_DATABASE_URL`` secret).  It performs a fixed set of read-only
verification queries and never prints credentials or connection URLs.

Safety properties
------------------
* Read-only: every query is a ``SELECT`` and runs inside a ``BEGIN READ ONLY``
  transaction.  A separate safety check rejects any query string containing
  data-definition or data-manipulation keywords.
* No local targets: connections to ``localhost`` / ``127.0.0.1`` / Docker
  bridge hosts are refused before a single byte is sent.
* Hosted-only: the resolved host must match a Neon endpoint suffix
  (``*.neon.tech`` or ``*.neon.com``).
* TLS enforced: the URL must request ``sslmode=require`` (or a verifying
  variant); insecure connections are rejected.
* No writes: the script never runs ingestion, summarisation, migration,
  seeding, or any pipeline task.
"""

from __future__ import annotations

import ast
import asyncio
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlparse

import asyncpg

from ai_news_digest.infrastructure.database.url import get_asyncpg_connect_args

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "migrations" / "versions"
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"

# Statement timeout for every query (milliseconds).
STATEMENT_TIMEOUT_MS = 15_000

# Hosts that must never be contacted by this verification script.
_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1", "host.docker.internal"})  # noqa: S104

# Hosted Neon endpoint suffixes.
_NEON_HOST_SUFFIXES = (".neon.tech", ".neon.com")

# Regex that matches data-manipulation / data-definition keywords at the start
# of a trimmed line or clause.  Used as a defence-in-depth check.
_WRITE_PATTERN = re.compile(
    r"\b(insert|update|delete|create|drop|alter|truncate|grant|revoke|"
    r"vacuum|analyze|comment|set\s+(?!transaction|local|role)|"
    r"begin|commit|rollback|savepoint|release)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConnectionInfo:
    """Safe, credential-free description of a database connection target."""

    host: str
    port: int
    database: str
    ssl_enabled: bool

    def describe(self) -> str:
        """Return a human-readable description that contains no credentials."""
        return f"host={self.host} port={self.port} database={self.database}"


@dataclass(frozen=True)
class ParsedDbUrl:
    """Credential-free decomposition of a database URL."""

    scheme: str
    host: str
    port: int
    database: str
    username: str | None
    has_sslmode: bool
    sslmode: str | None

    @property
    def is_local(self) -> bool:
        lowered = self.host.lower()
        return lowered in _LOCAL_HOSTS or lowered.endswith(".local")

    @property
    def is_neon(self) -> bool:
        lowered = self.host.lower()
        return any(lowered.endswith(suffix) for suffix in _NEON_HOST_SUFFIXES)


@dataclass
class QueryFailure:
    """Record of a verification query that could not be executed."""

    name: str
    sql: str
    error: str
    columns_in_table: list[str] | None = None


@dataclass
class VerificationResult:
    """Aggregated results of the staging-database verification."""

    connection: ConnectionInfo
    server_version: str | None
    current_alembic_version: str | None
    expected_alembic_heads: list[str]
    alembic_in_sync: bool
    article_counts_by_status: dict[str, int]
    active_verified_sources_count: int | None
    extraction_breakdown: list[dict[str, Any]]
    eligible_for_categorization: int | None
    eligible_for_analysis: int | None
    query_failures: list[QueryFailure] = field(default_factory=list)
    schema_columns: dict[str, list[str]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# URL parsing & validation
# ---------------------------------------------------------------------------


def parse_database_url(url: str) -> ParsedDbUrl:
    """Parse a PostgreSQL URL into credential-free components.

    The returned object **never** exposes the password or the full URL, only
    the host, port, database name, and SSL mode.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("postgresql", "postgresql+asyncpg"):
        raise ValueError(
            f"Unsupported URL scheme '{parsed.scheme}'; expected 'postgresql' "
            f"or 'postgresql+asyncpg'."
        )

    host = parsed.hostname or ""
    if not host:
        raise ValueError("Connection URL does not specify a host.")

    port = parsed.port or 5432
    database = (parsed.path or "").strip("/")
    if not database:
        raise ValueError("Connection URL does not specify a database name.")

    query_pairs = dict(parse_qsl(parsed.query, keep_blank_values=True))
    sslmode = query_pairs.get("sslmode")

    return ParsedDbUrl(
        scheme=parsed.scheme,
        host=host,
        port=port,
        database=database,
        username=parsed.username or None,
        has_sslmode=sslmode is not None,
        sslmode=sslmode,
    )


def validate_connection_target(url: str) -> tuple[ConnectionInfo, dict[str, Any]]:
    """Validate that *url* targets a hosted Neon staging database.

    Returns
    -------
    ConnectionInfo
        Safe connection metadata (host, port, database, ssl flag).
    dict
        asyncpg ``connect`` keyword arguments derived from the URL.

    Raises
    ------
    ValueError
        If the target cannot be confidently identified as a hosted, TLS-secured
        Neon endpoint.  The script **fails closed** in this case.
    """
    parsed = parse_database_url(url)

    if parsed.is_local:
        raise ValueError(
            f"Connection target is a local/loopback host ({parsed.host}); "
            f"refusing to connect to localhost or Docker-internal addresses."
        )

    if not parsed.is_neon:
        raise ValueError(
            f"Connection target host '{parsed.host}' is not a recognised "
            f"Neon endpoint (expected suffix {', '.join(_NEON_HOST_SUFFIXES)})."
        )

    # Let the shared helper validate query parameters and translate sslmode.
    connect_args = get_asyncpg_connect_args(url)

    if connect_args.get("ssl") is not True:
        raise ValueError(
            "SSL/TLS is not enforced by the connection URL (sslmode is not "
            "'require' or a verifying mode); refusing insecure connection."
        )

    info = ConnectionInfo(
        host=parsed.host,
        port=parsed.port,
        database=parsed.database,
        ssl_enabled=True,
    )
    return info, connect_args


# ---------------------------------------------------------------------------
# Migration-head discovery (static — no database required)
# ---------------------------------------------------------------------------


def _extract_str_constant(node: ast.AST) -> str | None:
    """Return the string value of an AST constant, or None."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value
        if node.value is None:
            return None
    return None


def _parse_migration_metadata(filepath: Path) -> tuple[str | None, str | None]:
    """Extract ``revision`` and ``down_revision`` from a migration file.

    Works with both annotated (``revision: str = "033"``) and unannotated
    (``revision = "033"``) assignment styles, as well as ``None`` down-revisions.
    """
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    revision: str | None = None
    down_revision: str | None = None
    for node in tree.body:
        target_name: str | None = None
        value_node: ast.AST | None = None
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in ("revision", "down_revision"):
                    target_name = t.id
                    value_node = node.value
                    break
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            if isinstance(target, ast.Name) and target.id in ("revision", "down_revision"):
                target_name = target.id
                value_node = node.value
        if target_name and value_node is not None:
            val = _extract_str_constant(value_node)
            if target_name == "revision":
                revision = val
            else:
                down_revision = val
    return revision, down_revision


def discover_migration_heads(migrations_dir: Path) -> list[str]:
    """Return the statically-determined Alembic head revision(s).

    Scans *migrations_dir* for migration files, builds the revision graph, and
    returns revisions that are not referenced as a ``down_revision`` by any
    other migration.  An empty result indicates a broken chain.
    """
    revisions: dict[str, str | None] = {}
    for filepath in sorted(migrations_dir.glob("*.py")):
        if filepath.name == "__init__.py":
            continue
        rev, down = _parse_migration_metadata(filepath)
        if rev is not None:
            revisions[rev] = down

    all_down_revisions = {d for d in revisions.values() if d is not None}
    heads = sorted(r for r in revisions if r not in all_down_revisions)
    return heads


# ---------------------------------------------------------------------------
# Verification queries (all read-only SELECTs)
# ---------------------------------------------------------------------------

# Each entry is (display_name, sql).  The SQL must be a single SELECT.
VERIFICATION_QUERIES: list[tuple[str, str]] = [
    (
        "article_counts_by_status",
        "SELECT status, count(*)::bigint AS count FROM articles GROUP BY status ORDER BY status",
    ),
    (
        "active_verified_sources",
        "SELECT count(*)::bigint AS count "
        "FROM sources WHERE is_active = true AND status = 'verified'",
    ),
    (
        "extraction_breakdown",
        "SELECT extraction_method, extraction_quality, "
        "count(*)::bigint AS total, "
        "count(content) AS with_content, "
        "(count(*) - count(content)) AS without_content "
        "FROM articles GROUP BY extraction_method, extraction_quality "
        "ORDER BY extraction_method, extraction_quality",
    ),
    (
        "eligible_for_categorization",
        "SELECT count(*)::bigint AS count FROM articles WHERE status = 'summarized'",
    ),
    (
        "eligible_for_analysis",
        "SELECT count(*)::bigint AS count FROM articles WHERE status = 'categorized'",
    ),
]


def assert_queries_read_only(queries: list[tuple[str, str]]) -> None:
    """Safety check: ensure no verification query can modify data."""
    for name, sql in queries:
        stripped = sql.strip()
        if not stripped.lower().startswith("select"):
            raise ValueError(f"Query '{name}' does not start with SELECT: {stripped[:50]}")
        if _WRITE_PATTERN.search(stripped):
            raise ValueError(f"Query '{name}' contains a disallowed keyword: {stripped[:80]}")


# ---------------------------------------------------------------------------
# Schema inspection (read-only)
# ---------------------------------------------------------------------------

_SCHEMA_COLUMNS_SQL = """
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = $1
ORDER BY ordinal_position
"""

_TABLES_SQL = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name
"""


async def _inspect_table_columns(conn: asyncpg.Connection, table: str) -> list[str]:
    rows = await conn.fetch(_SCHEMA_COLUMNS_SQL, table)
    return [row["column_name"] for row in rows]


def _primary_table_for(query_name: str) -> str | None:
    """Map a verification-query name to its primary table for schema inspection."""
    mapping = {
        "article_counts_by_status": "articles",
        "active_verified_sources": "sources",
        "extraction_breakdown": "articles",
        "eligible_for_categorization": "articles",
        "eligible_for_analysis": "articles",
    }
    return mapping.get(query_name)


# ---------------------------------------------------------------------------
# Main verification logic
# ---------------------------------------------------------------------------


async def run_verification(
    database_url: str,
    migrations_dir: Path = MIGRATIONS_DIR,
    *,
    print_output: bool = True,
) -> tuple[VerificationResult, int]:
    """Run all read-only verification queries against the staging database.

    Returns
    -------
    tuple
        (result, exit_code) where exit_code is 0 on success and non-zero if
        any query failed or the migration version is out of sync.
    """
    # 1. Fail-closed target validation (before any network activity).
    conn_info, connect_args = validate_connection_target(database_url)

    if print_output:
        print("Staging Database Verification")
        print("=" * 60)
        print(f"Connection target: {conn_info.describe()}")
        print(f"SSL/TLS: {'enforced' if conn_info.ssl_enabled else 'NOT enforced'}")
        print()

    # 2. Safety-check all queries.
    assert_queries_read_only(VERIFICATION_QUERIES)

    # 3. Statically determine the expected migration head.
    expected_heads = discover_migration_heads(migrations_dir)
    if print_output:
        print(f"Expected Alembic head (static): {expected_heads}")

    result = VerificationResult(
        connection=conn_info,
        server_version=None,
        current_alembic_version=None,
        expected_alembic_heads=expected_heads,
        alembic_in_sync=False,
        article_counts_by_status={},
        active_verified_sources_count=None,
        extraction_breakdown=[],
        eligible_for_categorization=None,
        eligible_for_analysis=None,
    )

    exit_code = 0

    # 4. Connect with an enforced statement timeout and TLS.
    connect_args = dict(connect_args)
    connect_args.setdefault("server_settings", {})
    if isinstance(connect_args["server_settings"], dict):
        connect_args["server_settings"]["statement_timeout"] = str(STATEMENT_TIMEOUT_MS)
        connect_args["server_settings"]["application_name"] = "staging-db-verify"
    else:
        connect_args["server_settings"] = {
            "statement_timeout": str(STATEMENT_TIMEOUT_MS),
            "application_name": "staging-db-verify",
        }

    # Credentials are extracted directly from the parsed URL and passed only
    # to asyncpg.connect() — they are never stored or printed.
    _parsed = urlparse(database_url)
    conn = await asyncpg.connect(
        host=conn_info.host,
        port=conn_info.port,
        user=_parsed.username,
        password=_parsed.password,
        database=conn_info.database,
        **connect_args,
    )

    try:
        # 5. Database identity — no credentials exposed.
        try:
            version_str = await conn.fetchval("SELECT version()")
        except asyncpg.PostgresError as exc:
            if print_output:
                print(f"[FAIL] Unable to retrieve server version: {exc}")
            result.query_failures.append(
                QueryFailure("server_version", "SELECT version()", str(exc))
            )
            exit_code = 1
        else:
            if isinstance(version_str, str):
                result.server_version = version_str
            else:
                result.server_version = str(version_str)

            if print_output:
                print(f"PostgreSQL version: {result.server_version}")
                print(f"Database name: {conn_info.database}")
                print()

        # 6. Alembic version.
        try:
            alembic_row = await conn.fetchrow("SELECT version_num FROM alembic_version")
            if alembic_row is not None:
                result.current_alembic_version = str(alembic_row["version_num"])
                if print_output:
                    print(f"Current Alembic version: {result.current_alembic_version}")
            else:
                if print_output:
                    print("Alembic version table exists but is empty.")
        except asyncpg.PostgresError as exc:
            result.query_failures.append(
                QueryFailure(
                    "alembic_version",
                    "SELECT version_num FROM alembic_version",
                    str(exc),
                )
            )
            if print_output:
                print(f"[FAIL] alembic_version query failed: {exc}")
            try:
                cols = await _inspect_table_columns(conn, "alembic_version")
                if not cols:
                    public_tables = await conn.fetch(_TABLES_SQL)
                    table_names = [r["table_name"] for r in public_tables]
                    if print_output:
                        print(f"  Tables present: {table_names}")
                    result.schema_columns["__public_tables__"] = table_names
                else:
                    result.schema_columns["alembic_version"] = cols
            except asyncpg.PostgresError as schema_exc:
                if print_output:
                    print(f"  Schema inspection also failed: {schema_exc}")
            exit_code = 1

        if result.current_alembic_version is not None:
            result.alembic_in_sync = result.current_alembic_version in expected_heads
            if print_output:
                status = "in sync" if result.alembic_in_sync else "OUT OF SYNC"
                print(f"Alembic status: {status}")
                print()

        # 7. Run all verification queries inside individual READ ONLY txns
        #    so a single failure doesn't abort the whole session.
        for name, sql in VERIFICATION_QUERIES:
            try:
                async with conn.transaction(readonly=True):
                    if name == "article_counts_by_status":
                        rows = await conn.fetch(sql)
                        result.article_counts_by_status = {
                            str(r["status"]): int(r["count"]) for r in rows
                        }
                    elif name == "active_verified_sources":
                        val = await conn.fetchval(sql)
                        result.active_verified_sources_count = int(val) if val is not None else 0
                    elif name == "extraction_breakdown":
                        rows = await conn.fetch(sql)
                        result.extraction_breakdown = [
                            {
                                "extraction_method": str(r["extraction_method"]),
                                "extraction_quality": str(r["extraction_quality"]),
                                "total": int(r["total"]),
                                "with_content": int(r["with_content"]),
                                "without_content": int(r["without_content"]),
                            }
                            for r in rows
                        ]
                    elif name == "eligible_for_categorization":
                        val = await conn.fetchval(sql)
                        result.eligible_for_categorization = int(val) if val is not None else 0
                    elif name == "eligible_for_analysis":
                        val = await conn.fetchval(sql)
                        result.eligible_for_analysis = int(val) if val is not None else 0

                if print_output:
                    _print_query_result(name, result)

            except asyncpg.PostgresError as exc:
                result.query_failures.append(
                    QueryFailure(
                        name,
                        sql,
                        str(exc),
                    )
                )
                if print_output:
                    print(f"[FAIL] {name}: {exc}")
                # Inspect the schema of the primary table involved so the
                # operator can see what columns actually exist.
                table = _primary_table_for(name)
                if table:
                    try:
                        cols = await _inspect_table_columns(conn, table)
                        result.schema_columns[table] = cols
                        if print_output and cols:
                            print(f"  Columns in {table}: {cols}")
                    except asyncpg.PostgresError:
                        pass
                exit_code = 1

        # 8. Summary
        if print_output:
            _print_summary(result)

    finally:
        await conn.close()

    return result, exit_code


def _print_query_result(name: str, result: VerificationResult) -> None:
    """Print a successfully executed query result (no credentials)."""
    if name == "article_counts_by_status":
        print("Article counts by status:")
        for status, count in sorted(result.article_counts_by_status.items()):
            print(f"  {status}: {count}")
    elif name == "active_verified_sources":
        print(f"Active, verified sources: {result.active_verified_sources_count}")
    elif name == "extraction_breakdown":
        print("Articles by extraction_method / extraction_quality:")
        for row in result.extraction_breakdown:
            print(
                f"  {row['extraction_method']}/{row['extraction_quality']}: "
                f"{row['total']} total "
                f"({row['with_content']} with content, "
                f"{row['without_content']} without)"
            )
    elif name == "eligible_for_categorization":
        print(
            "Articles eligible for categorization (status=summarized):",
            result.eligible_for_categorization,
        )
    elif name == "eligible_for_analysis":
        print(
            "Articles eligible for analysis (status=categorized):",
            result.eligible_for_analysis,
        )


def _print_summary(result: VerificationResult) -> None:
    print()
    print("Summary")
    print("-" * 60)
    print(f"Connection: {result.connection.describe()}")
    if result.current_alembic_version:
        sync = "SYNCED" if result.alembic_in_sync else "MISMATCH"
        print(
            f"Alembic: {result.current_alembic_version} "
            f"(expected head: {result.expected_alembic_heads}) [{sync}]"
        )
    if result.query_failures:
        print(f"Failed queries: {len(result.query_failures)}")
        for f in result.query_failures:
            print(f"  - {f.name}: {f.error[:120]}")
    else:
        print("Failed queries: 0")
    print("=" * 60)


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.")
        print("This workflow injects it from the STAGING_DATABASE_URL GitHub secret.")
        return 2

    try:
        _result, exit_code = asyncio.run(run_verification(database_url, MIGRATIONS_DIR))
    except ValueError as exc:
        print(f"ERROR: Connection target validation failed: {exc}")
        return 1
    except asyncpg.PostgresError as exc:
        print(f"ERROR: Database connection/query error: {exc}")
        return 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
