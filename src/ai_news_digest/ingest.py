from __future__ import annotations

import asyncio

from ai_news_digest.bootstrap.container import Container
from ai_news_digest.cli.printer import ConsolePrinter
from ai_news_digest.infrastructure.database.session import (
    get_db_session,
)


async def main() -> None:
    """
    Application entry point.

    Opens a database session, constructs the dependency
    container, runs the ingestion use case and prints
    the final summary.
    """

    ConsolePrinter.print_header()

    async for session in get_db_session():
        container = Container(session)

        summary = await (
            container.ingest_all_sources.execute()
        )

        ConsolePrinter.print_summary(
            summary,
        )


if __name__ == "__main__":
    asyncio.run(main())
