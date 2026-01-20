"""
Game state management - OWNS active_games table
"""
import json
from typing import Optional, Dict, Any
from db.connection import get_db


async def create_game(
    chat_id: int,
    game_type: str,
    player1_id: int,
    player2_id: int,
    bet_amount: int,
    initial_state: Dict[str, Any]
) -> int:
    """Create new game, returns game_id"""
    async with await get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO active_games
            (chat_id, game_type, player1_id, player2_id, bet_amount, game_state, current_turn)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (chat_id, game_type, player1_id, player2_id, bet_amount, json.dumps(initial_state), player1_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_active_game(chat_id: int) -> Optional[Dict[str, Any]]:
    """Get active game for chat"""
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT game_id, game_type, player1_id, player2_id, bet_amount, game_state, current_turn
            FROM active_games
            WHERE chat_id = ? AND winner_id IS NULL
            """,
            (chat_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return None
        
        return {
            'game_id': row['game_id'],
            'game_type': row['game_type'],
            'player1_id': row['player1_id'],
            'player2_id': row['player2_id'],
            'bet_amount': row['bet_amount'],
            'state': json.loads(row['game_state']),
            'current_turn': row['current_turn']
        }


async def update_game_state(game_id: int, new_state: Dict[str, Any], current_turn: int):
    """Update game state and current turn"""
    async with await get_db() as db:
        await db.execute(
            """
            UPDATE active_games
            SET game_state = ?, current_turn = ?
            WHERE game_id = ?
            """,
            (json.dumps(new_state), current_turn, game_id)
        )
        await db.commit()


async def end_game(game_id: int, winner_id: Optional[int]):
    """Mark game as ended with optional winner"""
    async with await get_db() as db:
        await db.execute(
            """
            UPDATE active_games
            SET winner_id = ?, ended_at = CURRENT_TIMESTAMP
            WHERE game_id = ?
            """,
            (winner_id, game_id)
        )
        await db.commit()


async def force_end_chat_games(chat_id: int):
    """Force end all active games in chat (when chat ends)"""
    async with await get_db() as db:
        await db.execute(
            """
            UPDATE active_games
            SET ended_at = CURRENT_TIMESTAMP
            WHERE chat_id = ? AND winner_id IS NULL
            """,
            (chat_id,)
        )
        await db.commit()


async def get_game_by_id(game_id: int) -> Optional[Dict[str, Any]]:
    """Get game by ID"""
    async with await get_db() as db:
        cursor = await db.execute(
            """
            SELECT game_type, player1_id, player2_id, bet_amount, game_state, current_turn, winner_id
            FROM active_games
            WHERE game_id = ?
            """,
            (game_id,)
        )
        row = await cursor.fetchone()
        
        if not row:
            return None
        
        return {
            'game_type': row['game_type'],
            'player1_id': row['player1_id'],
            'player2_id': row['player2_id'],
            'bet_amount': row['bet_amount'],
            'state': json.loads(row['game_state']),
            'current_turn': row['current_turn'],
            'winner_id': row['winner_id']
        }
