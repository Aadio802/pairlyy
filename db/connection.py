"""
SINGLE DATABASE ENTRY POINT (SAFE)
This is the ONLY file that opens SQLite connections
"""

print("BOOT: db.connection module loaded")

import aiosqlite
import asyncio
from config import settings
from pathlib import Path

_db = None
_db_lock = asyncio.Lock()


async def get_db():
    global _db

    print("BOOT: get_db() called")

    async with _db_lock:
        if _db is None:
            print("BOOT: creating SQLite connection")

            _db = await aiosqlite.connect(
                settings.DATABASE_PATH,
                isolation_level=None,
                check_same_thread=False,
            )

            _db.row_factory = aiosqlite.Row
            await _db.execute("PRAGMA journal_mode=WAL")
            await _db.execute("PRAGMA foreign_keys=ON")
            await _db.execute("PRAGMA busy_timeout = 5000")

        return _db


async def init_database():
    print("BOOT: init_database() called")

    schema_path = Path(__file__).parent / "schema.sql"
    db = await get_db()

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()

    await db.executescript(schema)
    print("BOOT: database schema loaded")
