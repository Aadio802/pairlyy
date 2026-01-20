"""
Rating handler - NO SQL, uses db modules
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.ratings import add_rating, get_pending_ratings
from db.sunflowers import add_sunflowers
from db.users import transition_state, UserState

router = Router()


async def show_rating_prompt(bot: Bot, rater_id: int, rated_user_id: int):
    """Show rating prompt"""
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text=f"{i} ⭐", callback_data=f"rate:{rated_user_id}:{i}")
    builder.adjust(5)
    
    await bot.send_message(
        rater_id,
        "Please rate your last partner:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("rate:"))
async def handle_rating(callback: CallbackQuery):
    """Handle rating submission"""
    parts = callback.data.split(":")
    rated_user_id = int(parts[1])
    rating = int(parts[2])
    user_id = callback.from_user.id
    
    # Save rating (removes from pending automatically)
    await add_rating(rated_user_id, user_id, rating)
    
    # Award sunflowers
    if rating >= 4:
        await add_sunflowers(user_id, 10, 'rating')
        await add_sunflowers(rated_user_id, 20, 'rating')
    
    await callback.message.edit_text("✅ Thanks for your rating!")
    
    # Check if done rating
    pending = await get_pending_ratings(user_id)
    if not pending:
        # All ratings done, transition RATING → IDLE
        await transition_state(user_id, UserState.RATING, UserState.IDLE)
    
    await callback.answer()
