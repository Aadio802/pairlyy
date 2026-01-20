"""
Streak management - OWNS streaks table
"""
from datetime import date, datetime
from db.connection import get_db
from config import settings


async def update_streak(user_id: int):
    """
    Update user's streak based on today's activity.
    Awards sunflowers if eligible.
    Uses pets if streak would break.
    """
    # Import here to avoid circular dependency
    from db.sunflowers import add_sunflowers, reset_streak_sunflowers
    from db.pets import use_pet
    from db.gardens import degrade_garden, destroy_garden
    
    today = date.today()
    
    async with await get_db() as db:
        # Get current streak
        cursor = await db.execute(
            "SELECT current_days, last_active_date FROM streaks WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            # First time - create streak
            await db.execute(
                "INSERT INTO streaks (user_id, current_days, last_active_date) VALUES (?, 1, ?)",
                (user_id, today.isoformat())
            )
            await db.commit()
            return
        
        current_days = row['current_days']
        last_active = row['last_active_date']
        
        if last_active:
            last_date = date.fromisoformat(last_active)
            days_diff = (today - last_date).days
            
            if days_diff == 0:
                # Same day, no update
                return
            elif days_diff == 1:
                # Continue streak
                new_days = current_days + 1
                
                await db.execute(
                    "UPDATE streaks SET current_days = ?, last_active_date = ? WHERE user_id = ?",
                    (new_days, today.isoformat(), user_id)
                )
                await db.commit()
                
                # Award sunflowers if eligible
                if new_days >= settings.STREAK_START_THRESHOLD:
                    await _award_streak_sunflowers(user_id, new_days)
            else:
                # Streak broken - try to use pet
                pet_used = await use_pet(user_id)
                
                if pet_used:
                    # Pet saved streak
                    await db.execute(
                        "UPDATE streaks SET last_active_date = ? WHERE user_id = ?",
                        (today.isoformat(), user_id)
                    )
                    await db.commit()
                else:
                    # Reset streak
                    await db.execute(
                        "UPDATE streaks SET current_days = 1, last_active_date = ? WHERE user_id = ?",
                        (today.isoformat(), user_id)
                    )
                    await db.commit()
                    
                    # Remove streak sunflowers
                    await reset_streak_sunflowers(user_id)
                    
                    # Destroy garden
                    await destroy_garden(user_id)
        else:
            # No last_active, start fresh
            await db.execute(
                "UPDATE streaks SET current_days = 1, last_active_date = ? WHERE user_id = ?",
                (today.isoformat(), user_id)
            )
            await db.commit()


async def _award_streak_sunflowers(user_id: int, streak_days: int):
    """Award sunflowers based on streak multiplier"""
    from db.sunflowers import add_sunflowers
    
    multiplier = 1.0
    
    if streak_days >= 30:
        multiplier = settings.STREAK_30D_MULTIPLIER
    elif streak_days >= 7:
        multiplier = settings.STREAK_7D_MULTIPLIER
    
    reward = int(settings.BASE_STREAK_REWARD * multiplier)
    await add_sunflowers(user_id, reward, 'streak')


async def get_streak_days(user_id: int) -> int:
    """Get current streak days"""
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT current_days FROM streaks WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row['current_days'] if row else 0
