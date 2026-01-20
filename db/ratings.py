"""
Rating system - OWNS ratings and pending_ratings tables
"""
from typing import Optional, Tuple, List
from db.connection import get_db
from config import settings


async def add_rating(rated_user_id: int, rater_user_id: int, rating: int):
    """Add or update rating and remove from pending"""
    async with await get_db() as db:
        async with db.execute("BEGIN"):
            # Insert rating
            await db.execute(
                """
                INSERT OR REPLACE INTO ratings (rated_user_id, rater_user_id, rating)
                VALUES (?, ?, ?)
                """,
                (rated_user_id, rater_user_id, rating)
            )
            
            # Remove from pending
            await db.execute(
                """
                DELETE FROM pending_ratings
                WHERE rater_id = ? AND rated_user_id = ?
                """,
                (rater_user_id, rated_user_id)
            )
            
            await db.commit()


async def get_average_rating(user_id: int) -> Optional[Tuple[float, int]]:
    """
    Get average rating and count.
    Returns (avg, count) if count >= MIN_RATINGS_FOR_DISPLAY, else None.
    """
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT AVG(rating), COUNT(*)
            FROM ratings
            WHERE rated_user_id = ?
            """,
            (user_id,)
        )
        row = await cursor.fetchone()
        
        if row and row[1] >= settings.MIN_RATINGS_FOR_DISPLAY:
            return (round(row[0], 1), row[1])
        
        return None


async def get_pending_ratings(user_id: int) -> List[int]:
    """Get list of user_ids that this user needs to rate"""
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT rated_user_id
            FROM pending_ratings
            WHERE rater_id = ?
            ORDER BY created_at ASC
            """,
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [row['rated_user_id'] for row in rows]


async def has_pending_rating(user_id: int, rated_user_id: int) -> bool:
    """Check if user has specific pending rating"""
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT 1 FROM pending_ratings
            WHERE rater_id = ? AND rated_user_id = ?
            """,
            (user_id, rated_user_id)
        )
        return await cursor.fetchone() is not None
