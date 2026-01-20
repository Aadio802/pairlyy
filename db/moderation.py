"""
Moderation system - OWNS violations, bans, link_tracking, monitored_messages tables
"""
from typing import Optional, Tuple
from datetime import datetime, timedelta, date
from db.connection import get_db


async def log_violation(user_id: int, violation_type: str):
    """Log user violation"""
    async with await get_db() as db:
        await db.execute(
            """
            INSERT INTO violations (user_id, violation_type)
            VALUES (?, ?)
            """,
            (user_id, violation_type)
        )
        await db.commit()


async def get_violation_count(user_id: int, violation_type: str, hours: int = 24) -> int:
    """Get violation count in last N hours"""
    cutoff = datetime.now() - timedelta(hours=hours)
    
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM violations
            WHERE user_id = ? AND violation_type = ? AND occurred_at > ?
            """,
            (user_id, violation_type, cutoff.isoformat())
        )
        return (await cursor.fetchone())[0]


async def ban_user(user_id: int, hours: int, reason: str):
    """Ban user for specified hours"""
    banned_until = datetime.now() + timedelta(hours=hours)
    
    async with await get_db() as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO bans (user_id, reason, banned_until)
            VALUES (?, ?, ?)
            """,
            (user_id, reason, banned_until.isoformat())
        )
        await db.commit()


async def unban_user(user_id: int):
    """Remove ban from user"""
    async with await get_db() as db:
        await db.execute(
            "DELETE FROM bans WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def is_banned(user_id: int) -> Optional[Tuple[datetime, str]]:
    """
    Check if user is banned.
    Returns (banned_until, reason) or None.
    """
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT banned_until, reason
            FROM bans
            WHERE user_id = ? AND banned_until > ?
            """,
            (user_id, datetime.now().isoformat())
        )
        row = await cursor.fetchone()
        
        if row:
            return (datetime.fromisoformat(row['banned_until']), row['reason'])
        
        return None


async def get_link_count_today(user_id: int) -> int:
    """Get number of links sent today"""
    today = date.today()
    
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT count
            FROM link_tracking
            WHERE user_id = ? AND date = ?
            """,
            (user_id, today.isoformat())
        )
        row = await cursor.fetchone()
        return row['count'] if row else 0


async def increment_link_count(user_id: int):
    """Increment today's link count"""
    today = date.today()
    
    async with await get_db() as db:
        await db.execute(
            """
            INSERT INTO link_tracking (user_id, date, count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, date)
            DO UPDATE SET count = count + 1
            """,
            (user_id, today.isoformat())
        )
        await db.commit()


async def log_monitored_message(
    chat_id: int,
    sender_id: int,
    message_type: str,
    content: Optional[str] = None,
    media_file_id: Optional[str] = None
):
    """Log message for admin monitoring"""
    async with await get_db() as db:
        await db.execute(
            """
            INSERT INTO monitored_messages (chat_id, sender_id, message_type, content, media_file_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, sender_id, message_type, content, media_file_id)
        )
        await db.commit()


async def get_recent_messages(limit: int = 50):
    """Get recent monitored messages"""
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT chat_id, sender_id, message_type, content, sent_at
            FROM monitored_messages
            ORDER BY sent_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def clean_expired_bans():
    """Remove expired bans"""
    async with await get_db() as db:
        await db.execute(
            "DELETE FROM bans WHERE banned_until <= ?",
            (datetime.now().isoformat(),)
        )
        await db.commit()


async def get_all_user_ids():
    """Get all user IDs (for broadcasting)"""
    async with await get_db() as db:
        cursor = await db.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [row['user_id'] for row in rows]


async def get_bot_stats():
    """Get bot statistics"""
    async with await get_db() as db:
        stats = {}
        
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM users WHERE premium_until > CURRENT_TIMESTAMP"
        )
        stats['premium_users'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM active_chats")
        stats['active_chats'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM waiting_users")
        stats['searching'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM ratings")
        stats['total_ratings'] = (await cursor.fetchone())[0]
        
        cursor = await db.execute(
            "SELECT COUNT(*) FROM bans WHERE banned_until > CURRENT_TIMESTAMP"
        )
        stats['banned_users'] = (await cursor.fetchone())[0]
        
        return stats
