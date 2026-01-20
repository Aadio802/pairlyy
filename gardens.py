"""
Garden system - OWNS gardens table
"""
from typing import Optional, Tuple
from datetime import date
from db.connection import get_db


async def create_garden(user_id: int) -> bool:
    """Create level 1 garden for user"""
    async with await get_db() as db:
        try:
            await db.execute(
                """
                INSERT INTO gardens (user_id, level, last_harvest_date)
                VALUES (?, 1, ?)
                """,
                (user_id, date.today().isoformat())
            )
            await db.commit()
            return True
        except:
            return False


async def get_garden(user_id: int) -> Optional[Tuple[int, str]]:
    """Get garden info as (level, last_harvest_date)"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT level, last_harvest_date FROM gardens WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return (row['level'], row['last_harvest_date']) if row else None


async def harvest_garden(user_id: int) -> Optional[int]:
    """
    Harvest garden. Returns amount harvested or None if already harvested today.
    """
    from db.sunflowers import add_sunflowers
    
    garden = await get_garden(user_id)
    if not garden:
        return None
    
    level, last_harvest = garden
    today = date.today()
    
    if last_harvest:
        last_date = date.fromisoformat(last_harvest)
        if last_date >= today:
            return None  # Already harvested today
    
    # Calculate reward: Level 1=20, Level 2=40, Level 3=60
    reward = level * 20
    
    # Award sunflowers
    await add_sunflowers(user_id, reward, 'game')
    
    # Update last harvest
    async with await get_db() as db:
        await db.execute(
            "UPDATE gardens SET last_harvest_date = ? WHERE user_id = ?",
            (today.isoformat(), user_id)
        )
        await db.commit()
    
    return reward


async def upgrade_garden(user_id: int) -> bool:
    """Upgrade garden to next level (max 3)"""
    async with await get_db() as db:
        cursor = await db.execute(
            "UPDATE gardens SET level = MIN(3, level + 1) WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def degrade_garden(user_id: int):
    """Downgrade garden by one level"""
    async with await get_db() as db:
        await db.execute(
            "UPDATE gardens SET level = MAX(1, level - 1) WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def destroy_garden(user_id: int):
    """Completely remove garden"""
    async with await get_db() as db:
        await db.execute(
            "DELETE FROM gardens WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def has_garden(user_id: int) -> bool:
    """Check if user has a garden"""
    return await get_garden(user_id) is not None
