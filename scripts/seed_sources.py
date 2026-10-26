from __future__ import annotations

import asyncio

from ai_news_digest.scripts import seed_sources as _canonical
from ai_news_digest.scripts.seed_sources import main as _canonical_main

DEFAULT_SOURCES = _canonical.DEFAULT_SOURCES
get_db_session = _canonical.get_db_session
Container = _canonical.Container


async def main() -> None:
    """Compatibility entry point for the canonical source seeder."""
    await _canonical_main()


if __name__ == "__main__":
    asyncio.run(main())
