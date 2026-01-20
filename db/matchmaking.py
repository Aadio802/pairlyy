"""
Matchmaking database operations
OWNS: waiting_users, active_chats, match_history
"""
from typing import Optional, List
from datetime import datetime, timedelta
from db.connection import get_db
from config import settings


async def join_waiting_pool(
    user_id: int,
    gender: str,
    is_premium: bool,
    rating: Optional[float],
    rating_count: int,
    gender_preference: Optional[str]
):
    """Add user to waiting pool"""
    async with await get_db() as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO waiting_users
            (user_id, gender, is_premium, rating, rating_count, gender_preference, joined_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (user_id, gender, 1 if is_premium else 0, rating, rating_count, gender_preference)
        )
        await db.commit()


async def leave_waiting_pool(user_id: int):
    """Remove user from waiting pool"""
    async with await get_db() as db:
        await db.execute(
            "DELETE FROM waiting_users WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def get_waiting_candidates(user_id: int) -> List[dict]:
    """
    Get candidates from waiting pool, excluding recent matches.
    Returns list of dicts with user info.
    """
    cutoff_time = datetime.now() - timedelta(seconds=settings.MATCH_HISTORY_WINDOW_SECONDS)
    
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT w.user_id, w.gender, w.is_premium, w.rating, w.rating_count, w.joined_at
            FROM waiting_users w
            WHERE w.user_id != ?
            AND w.user_id NOT IN (
                SELECT partner_id
                FROM match_history
                WHERE user_id = ?
                AND last_matched_at > ?
            )
            """,
            (user_id, user_id, cutoff_time.isoformat())
        )
        
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def create_match_atomic(user_a: int, user_b: int) -> int:
    """
    ATOMIC TRANSACTION: Create match between two users.
    
    Steps:
    1. Remove both from waiting pool
    2. Create active chat
    3. Update user partners
    4. Record match history
    
    Returns chat_id on success, 0 on failure.
    """
    async with await get_db() as db:
        async with db.execute("BEGIN IMMEDIATE"):
            try:
                # Step 1: Remove from waiting pool
                await db.execute(
                    "DELETE FROM waiting_users WHERE user_id IN (?, ?)",
                    (user_a, user_b)
                )
                
                # Step 2: Create active chat
                cursor = await db.execute(
                    """
                    INSERT INTO active_chats (user_a, user_b, started_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    """,
                    (user_a, user_b)
                )
                chat_id = cursor.lastrowid
                
                # Step 3: Update user partners
                await db.execute(
                    "UPDATE users SET partner_id = ?, current_state = 'CHATTING' WHERE user_id = ?",
                    (user_b, user_a)
                )
                
                await db.execute(
                    "UPDATE users SET partner_id = ?, current_state = 'CHATTING' WHERE user_id = ?",
                    (user_a, user_b)
                )
                
                # Step 4: Record match history
                now = datetime.now().isoformat()
                await db.execute(
                    "INSERT OR REPLACE INTO match_history (user_id, partner_id, last_matched_at) VALUES (?, ?, ?)",
                    (user_a, user_b, now)
                )
                await db.execute(
                    "INSERT OR REPLACE INTO match_history (user_id, partner_id, last_matched_at) VALUES (?, ?, ?)",
                    (user_b, user_a, now)
                )
                
                await db.commit()
                return chat_id
                
            except Exception as e:
                await db.execute("ROLLBACK")
                print(f"Match creation failed: {e}")
                return 0


async def end_chat_atomic(user_a: int, user_b: int):
    """
    ATOMIC TRANSACTION: End chat between users.
    
    Steps:
    1. End any active game
    2. Delete active chat
    3. Clear partner references
    4. Create pending ratings
    """
    async with await get_db() as db:
        async with db.execute("BEGIN IMMEDIATE"):
            try:
                # Step 1: Get chat_id
                cursor = await db.execute(
                    """
                    SELECT chat_id FROM active_chats
                    WHERE (user_a = ? AND user_b = ?) OR (user_a = ? AND user_b = ?)
                    """,
                    (user_a, user_b, user_b, user_a)
                )
                chat_row = await cursor.fetchone()
                
                if chat_row:
                    chat_id = chat_row['chat_id']
                    
                    # End active game
                    await db.execute(
                        """
                        UPDATE active_games
                        SET ended_at = CURRENT_TIMESTAMP
                        WHERE chat_id = ? AND winner_id IS NULL
                        """,
                        (chat_id,)
                    )
                    
                    # Delete active chat
                    await db.execute(
                        "DELETE FROM active_chats WHERE chat_id = ?",
                        (chat_id,)
                    )
                
                # Step 2: Clear partners
                await db.execute(
                    "UPDATE users SET partner_id = NULL WHERE user_id IN (?, ?)",
                    (user_a, user_b)
                )
                
                # Step 3: Create pending ratings
                await db.execute(
                    "INSERT OR IGNORE INTO pending_ratings (rater_id, rated_user_id) VALUES (?, ?)",
                    (user_a, user_b)
                )
                await db.execute(
                    "INSERT OR IGNORE INTO pending_ratings (rater_id, rated_user_id) VALUES (?, ?)",
                    (user_b, user_a)
                )
                
                await db.commit()
                
            except Exception as e:
                await db.execute("ROLLBACK")
                print(f"Chat end failed: {e}")


async def get_chat_id(user_id: int) -> Optional[int]:
    """Get active chat_id for user"""
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT chat_id FROM active_chats
            WHERE user_a = ? OR user_b = ?
            """,
            (user_id, user_id)
        )
        row = await cursor.fetchone()
        return row['chat_id'] if row else None


async def is_in_waiting_pool(user_id: int) -> bool:
    """Check if user is in waiting pool"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT 1 FROM waiting_users WHERE user_id = ?",
            (user_id,)
        )
        return await cursor.fetchone() is not None
