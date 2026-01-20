"""
Pet system - OWNS pets table
"""
from typing import List, Tuple
from db.connection import get_db
from config import settings


async def add_pet(user_id: int, pet_type: str, saves: int = 1) -> bool:
    """
    Add pet to user. Returns False if max pets reached.
    """
    async with await get_db() as db:
        # Check current count
        cursor = await db.execute(
            "SELECT COUNT(*) FROM pets WHERE user_id = ?",
            (user_id,)
        )
        count = (await cursor.fetchone())[0]
        
        if count >= settings.MAX_PETS:
            return False
        
        # Add pet
        await db.execute(
            """
            INSERT INTO pets (user_id, pet_type, saves_remaining)
            VALUES (?, ?, ?)
            """,
            (user_id, pet_type, saves)
        )
        await db.commit()
        return True


async def use_pet(user_id: int) -> bool:
    """
    Use one pet to save streak.
    Auto-consumes pet.
    Returns True if pet was used, False if no pets available.
    """
    async with await get_db() as db:
        async with db.execute("BEGIN"):
            # Get oldest pet
            cursor = await db.execute(
                """
                SELECT id, saves_remaining
                FROM pets
                WHERE user_id = ?
                ORDER BY id ASC
                LIMIT 1
                """,
                (user_id,)
            )
            row = await cursor.fetchone()
            
            if not row:
                await db.execute("ROLLBACK")
                return False
            
            pet_id = row['id']
            saves = row['saves_remaining']
            
            if saves > 1:
                # Decrement saves
                await db.execute(
                    "UPDATE pets SET saves_remaining = saves_remaining - 1 WHERE id = ?",
                    (pet_id,)
                )
            else:
                # Remove pet
                await db.execute(
                    "DELETE FROM pets WHERE id = ?",
                    (pet_id,)
                )
            
            await db.commit()
            return True


async def get_pets(user_id: int) -> List[Tuple[int, str, int]]:
    """Get all pets for user as (id, type, saves)"""
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, pet_type, saves_remaining
            FROM pets
            WHERE user_id = ?
            ORDER BY id
            """,
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [(row['id'], row['pet_type'], row['saves_remaining']) for row in rows]


async def get_pet_count(user_id: int) -> int:
    """Get total pet count"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM pets WHERE user_id = ?",
            (user_id,)
        )
        return (await cursor.fetchone())[0]
