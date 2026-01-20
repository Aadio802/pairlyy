"""
SINGLE DATABASE ENTRY POINT
This is the ONLY file that opens SQLite connections
"""
import aiosqlite
from config import settings
from pathlib import Path


async def get_db() -> aiosqlite.Connection:
    """
    Get database connection with WAL mode and foreign keys enabled.
    
    This is the ONLY function allowed to create database connections.
    All other modules MUST use this function.
    
    Returns:
        Async SQLite connection with:
        - WAL mode enabled
        - Foreign keys enabled
        - Row factory set
    """
    conn = await aiosqlite.connect(settings.DATABASE_PATH)
    conn.row_factory = aiosqlite.Row
    
    # Enable WAL mode for better concurrency
    await conn.execute("PRAGMA journal_mode=WAL")
    
    # Enable foreign keys
    await conn.execute("PRAGMA foreign_keys=ON")
    
    return conn


async def init_database():
    """Initialize database schema from schema.sql"""
    schema_path = Path(__file__).parent / "schema.sql"
    
    async with await get_db() as db:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()
        
        await db.executescript(schema)
        await db.commit()
