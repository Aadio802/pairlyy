"""
SINGLE DATABASE ENTRY POINT (SAFE)
This is the ONLY file that opens SQLite connections
"""

import aiosqlite
import asyncio
from config import settings
from pathlib import Path

_db: aiosqlite.Connection | None = None
_db_lock = asyncio.Lock()


async def get_db() -> aiosqlite.Connection:
    """
    Return a SINGLE shared database connection.
    Safe for aiogram, Railway, and hot restarts.
    """
    global _db

    async with _db_lock:
        if _db is None:
            _db = await aiosqlite.connect(
                settings.DATABASE_PATH,
                isolation_level=None,
                check_same_thread=False,
            )

            _db.row_factory = aiosqlite.Row

            # WAL mode = concurrent reads
            await _db.execute("PRAGMA journal_mode=WAL")

            # Foreign keys
            await _db.execute("PRAGMA foreign_keys=ON")

            # Busy timeout to avoid "database is locked"
            await _db.execute("PRAGMA busy_timeout = 5000")

        return _db


async def init_database():
    """Initialize database schema from schema.sql"""
    schema_path = Path(__file__).parent / "schema.sql"

    db = await get_db()
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()

    await db.executescript(schema)
