"""
Match selection algorithm - NO SQL, pure business logic
"""
from typing import Optional
from datetime import datetime
from config import settings
from db.matchmaking import get_waiting_candidates, create_match_atomic
from db.users import is_premium


def calculate_match_score(candidate: dict, my_is_premium: bool, waiting_seconds: int) -> int:
    """
    Calculate match score for candidate.
    
    Score formula:
    - Base: 100
    - +25 if candidate is premium
    - +20 if I'm premium AND candidate rating >= 4.5
    - +10 if candidate rating >= 4.0
    - +1 per 10 seconds waiting time
    """
    score = 100
    
    # Candidate premium bonus
    if candidate['is_premium']:
        score += 25
    
    # Rating bonuses
    if candidate['rating']:
        if my_is_premium and candidate['rating'] >= 4.5:
            score += 20
        elif candidate['rating'] >= 4.0:
            score += 10
    
    # Waiting time bonus
    waiting_bonus = waiting_seconds // settings.WAITING_TIME_BONUS_INTERVAL
    score += waiting_bonus
    
    return score


async def find_best_match(user_id: int, gender_pref: Optional[str] = None) -> Optional[int]:
    """
    Find best match from waiting pool.
    Returns partner_id on success, None if no candidates.
    """
    # Get my premium status
    my_is_premium = await is_premium(user_id)
    
    # Get candidates
    candidates = await get_waiting_candidates(user_id)
    
    if not candidates:
        return None
    
    # Filter by gender preference
    if gender_pref:
        candidates = [c for c in candidates if c['gender'] == gender_pref]
    
    if not candidates:
        return None
    
    # Score all candidates
    now = datetime.now()
    scored_candidates = []
    
    for candidate in candidates:
        joined_at = datetime.fromisoformat(candidate['joined_at'])
        waiting_seconds = int((now - joined_at).total_seconds())
        
        score = calculate_match_score(
            candidate,
            my_is_premium,
            waiting_seconds
        )
        
        scored_candidates.append((candidate['user_id'], score))
    
    # Sort by score descending
    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    
    # Return best match
    return scored_candidates[0][0] if scored_candidates else None


async def create_match(user_a: int, user_b: int) -> tuple[bool, int]:
    """
    Create match between two users.
    Returns (success, chat_id).
    """
    chat_id = await create_match_atomic(user_a, user_b)
    return (chat_id > 0, chat_id)
