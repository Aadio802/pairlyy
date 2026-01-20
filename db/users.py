"""
User state management - OWNS users table EXCLUSIVELY
No other file touches users table
"""
from typing import Optional
from datetime import datetime, timedelta
from db.connection import get_db


class UserState:
    """FSM States - Must match DB CHECK constraint"""
    NEW = "NEW"
    AGREED = "AGREED"
    IDLE = "IDLE"
    SEARCHING = "SEARCHING"
    CHATTING = "CHATTING"
    RATING = "RATING"


async def user_exists(user_id: int) -> bool:
    """Check if user exists"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT 1 FROM users WHERE user_id = ?",
            (user_id,)
        )
        result = await cursor.fetchone()
        return result is not None


async def create_user(user_id: int, gender: str):
    """Create new user in NEW state"""
    async with await get_db() as db:
        await db.execute(
            """
            INSERT INTO users (user_id, gender, current_state)
            VALUES (?, ?, ?)
            """,
            (user_id, gender, UserState.NEW)
        )
        await db.commit()


async def get_user_state(user_id: int) -> Optional[str]:
    """Get current FSM state"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT current_state FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row['current_state'] if row else None


async def transition_state(user_id: int, from_state: str, to_state: str) -> bool:
    """
    Atomic state transition with validation.
    Returns True if transition succeeded, False if user was not in from_state.
    """
    async with await get_db() as db:
        cursor = await db.execute(
            """
            UPDATE users
            SET current_state = ?, last_active = CURRENT_TIMESTAMP
            WHERE user_id = ? AND current_state = ?
            """,
            (to_state, user_id, from_state)
        )
        await db.commit()
        return cursor.rowcount > 0


async def force_set_state(user_id: int, state: str):
    """Force set state (use with extreme caution)"""
    async with await get_db() as db:
        await db.execute(
            "UPDATE users SET current_state = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
            (state, user_id)
        )
        await db.commit()


async def get_user(user_id: int) -> Optional[dict]:
    """Get complete user record"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_partner_id(user_id: int) -> Optional[int]:
    """Get user's current partner"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT partner_id FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row['partner_id'] if row and row['partner_id'] else None


async def set_partner(user_id: int, partner_id: Optional[int]):
    """Set user's partner (used by matchmaking.py ONLY)"""
    async with await get_db() as db:
        await db.execute(
            "UPDATE users SET partner_id = ? WHERE user_id = ?",
            (partner_id, user_id)
        )
        await db.commit()


async def is_premium(user_id: int) -> bool:
    """Check if user has active premium"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT premium_until FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        if row and row['premium_until']:
            premium_until = datetime.fromisoformat(row['premium_until'])
            return premium_until > datetime.now()
        
        return False


async def update_premium(user_id: int, days: int):
    """Add premium days to user"""
    premium_until = datetime.now() + timedelta(days=days)
    
    async with await get_db() as db:
        await db.execute(
            "UPDATE users SET premium_until = ? WHERE user_id = ?",
            (premium_until.isoformat(), user_id)
        )
        await db.commit()


async def get_premium_days_remaining(user_id: int) -> int:
    """Get remaining premium days"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT premium_until FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        if row and row['premium_until']:
            premium_until = datetime.fromisoformat(row['premium_until'])
            if premium_until > datetime.now():
                return (premium_until - datetime.now()).days
        
        return 0


async def get_gender(user_id: int) -> Optional[str]:
    """Get user's gender"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT gender FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row['gender'] if row else None


async def can_use_temp_premium(user_id: int) -> bool:
    """Check if user can use temp premium (15-day cooldown)"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT temp_premium_last_used FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        if not row or not row['temp_premium_last_used']:
            return True
        
        last_used = datetime.fromisoformat(row['temp_premium_last_used'])
        days_since = (datetime.now() - last_used).days
        
        from config import settings
        return days_since >= settings.TEMP_PREMIUM_COOLDOWN_DAYS


async def use_temp_premium(user_id: int):
    """Mark temp premium as used and activate premium"""
    from config import settings
    
    async with await get_db() as db:
        premium_until = datetime.now() + timedelta(days=settings.TEMP_PREMIUM_DAYS)
        
        await db.execute(
            """
            UPDATE users
            SET temp_premium_last_used = CURRENT_TIMESTAMP,
                premium_until = ?
            WHERE user_id = ?
            """,
            (premium_until.isoformat(), user_id)
        )
        await db.commit()
