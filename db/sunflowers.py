"""
Sunflower ledger system - OWNS sunflower_ledger table
"""
from typing import Dict
from db.connection import get_db


async def add_sunflowers(user_id: int, amount: int, source: str):
    """
    Add sunflowers to ledger (append-only).
    source must be: 'streak', 'game', 'gift', or 'rating'
    """
    if amount <= 0:
        return
    
    async with await get_db() as db:
        await db.execute(
            """
            INSERT INTO sunflower_ledger (user_id, source, amount)
            VALUES (?, ?, ?)
            """,
            (user_id, source, amount)
        )
        await db.commit()


async def remove_sunflowers(user_id: int, amount: int, source: str):
    """
    Remove sunflowers from specific source (negative ledger entry).
    Returns actual amount removed.
    """
    if amount <= 0:
        return 0
    
    async with await get_db() as db:
        await db.execute(
            """
            INSERT INTO sunflower_ledger (user_id, source, amount)
            VALUES (?, ?, ?)
            """,
            (user_id, source, -amount)
        )
        await db.commit()
        return amount


async def get_sunflower_balance(user_id: int) -> Dict[str, int]:
    """
    Get sunflower balance by source.
    Returns: {'streak': X, 'game': Y, 'gift': Z, 'rating': W, 'total': SUM}
    """
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT source, SUM(amount)
            FROM sunflower_ledger
            WHERE user_id = ?
            GROUP BY source
            """,
            (user_id,)
        )
        rows = await cursor.fetchall()
        
        balance = {'streak': 0, 'game': 0, 'gift': 0, 'rating': 0}
        
        for row in rows:
            source = row[0]
            amount = row[1]
            if source in balance:
                balance[source] = max(0, amount)  # Never negative display
        
        balance['total'] = sum(balance.values())
        return balance


async def deduct_sunflowers_smart(user_id: int, amount: int) -> bool:
    """
    Deduct sunflowers with priority: game > gift > rating > streak.
    Returns True if successful, False if insufficient balance.
    """
    balance = await get_sunflower_balance(user_id)
    
    if balance['total'] < amount:
        return False
    
    remaining = amount
    
    async with await get_db() as db:
        async with db.execute("BEGIN"):
            # Deduct from game first
            if balance['game'] > 0:
                deduct = min(balance['game'], remaining)
                await db.execute(
                    "INSERT INTO sunflower_ledger (user_id, source, amount) VALUES (?, 'game', ?)",
                    (user_id, -deduct)
                )
                remaining -= deduct
            
            # Then gift
            if remaining > 0 and balance['gift'] > 0:
                deduct = min(balance['gift'], remaining)
                await db.execute(
                    "INSERT INTO sunflower_ledger (user_id, source, amount) VALUES (?, 'gift', ?)",
                    (user_id, -deduct)
                )
                remaining -= deduct
            
            # Then rating
            if remaining > 0 and balance['rating'] > 0:
                deduct = min(balance['rating'], remaining)
                await db.execute(
                    "INSERT INTO sunflower_ledger (user_id, source, amount) VALUES (?, 'rating', ?)",
                    (user_id, -deduct)
                )
                remaining -= deduct
            
            # Finally streak
            if remaining > 0 and balance['streak'] > 0:
                deduct = min(balance['streak'], remaining)
                await db.execute(
                    "INSERT INTO sunflower_ledger (user_id, source, amount) VALUES (?, 'streak', ?)",
                    (user_id, -deduct)
                )
                remaining -= deduct
            
            await db.commit()
    
    return True


async def reset_streak_sunflowers(user_id: int):
    """Remove all streak-sourced sunflowers (on streak break)"""
    balance = await get_sunflower_balance(user_id)
    
    if balance['streak'] > 0:
        await remove_sunflowers(user_id, balance['streak'], 'streak')
