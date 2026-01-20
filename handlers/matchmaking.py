"""
Matchmaking handlers - NO SQL, uses db modules and services
"""
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.users import (
    user_exists, get_user_state, UserState, transition_state,
    get_partner_id, is_premium, get_gender
)
from db.matchmaking import join_waiting_pool, leave_waiting_pool, end_chat_atomic
from db.ratings import get_average_rating
from db.streaks import update_streak
from services.matcher import find_best_match, create_match

router = Router()


@router.message(Command("find"))
async def cmd_find(message: Message):
    """Find a chat partner"""
    user_id = message.from_user.id
    
    # Validate user exists
    if not await user_exists(user_id):
        await message.answer("Please use /start first.")
        return
    
    state = await get_user_state(user_id)
    
    # State validation
    if state == UserState.CHATTING:
        await message.answer("You are already in a chat. Use /next or /stop.")
        return
    
    if state == UserState.SEARCHING:
        await message.answer("Already searching for a partner…")
        return
    
    # Update streak
    await update_streak(user_id)
    
    # Check for premium and gender preference
    user_is_premium = await is_premium(user_id)
    
    if user_is_premium:
        builder = InlineKeyboardBuilder()
        builder.button(text="Any Gender", callback_data="pref:any")
        builder.button(text="Male", callback_data="pref:male")
        builder.button(text="Female", callback_data="pref:female")
        builder.adjust(1)
        
        await message.answer(
            "🌟 Premium: Choose gender preference",
            reply_markup=builder.as_markup()
        )
    else:
        await start_matchmaking(message.bot, user_id, None)


@router.callback_query(F.data.startswith("pref:"))
async def select_preference(callback: CallbackQuery):
    """Handle premium gender preference"""
    user_id = callback.from_user.id
    pref = callback.data.split(":")[1]
    gender_pref = None if pref == "any" else pref
    
    await callback.message.delete()
    await start_matchmaking(callback.bot, user_id, gender_pref)
    await callback.answer()


async def start_matchmaking(bot: Bot, user_id: int, gender_pref: str = None):
    """Start matchmaking process"""
    # Transition to SEARCHING
    success = await transition_state(user_id, UserState.IDLE, UserState.SEARCHING)
    if not success:
        await bot.send_message(user_id, "Failed to start search. Try again.")
        return
    
    # Get user data
    gender = await get_gender(user_id)
    user_is_premium = await is_premium(user_id)
    rating_info = await get_average_rating(user_id)
    
    # Add to waiting pool
    await join_waiting_pool(
        user_id,
        gender,
        user_is_premium,
        rating_info[0] if rating_info else None,
        rating_info[1] if rating_info else 0,
        gender_pref
    )
    
    # Try to find match
    partner_id = await find_best_match(user_id, gender_pref)
    
    if partner_id:
        # Create match
        success, chat_id = await create_match(user_id, partner_id)
        
        if success:
            await notify_match(bot, user_id, partner_id)
        else:
            await bot.send_message(user_id, "🔍 Searching for a partner…")
    else:
        await bot.send_message(user_id, "🔍 Searching for a partner…")


async def notify_match(bot: Bot, user_a: int, user_b: int):
    """Notify both users of match"""
    rating_a = await get_average_rating(user_a)
    rating_b = await get_average_rating(user_b)
    
    msg_a = "✅ Partner found — "
    msg_a += f"⭐ {rating_b[0]} rated by {rating_b[1]} users" if rating_b else "New user (no ratings yet)"
    
    msg_b = "✅ Partner found — "
    msg_b += f"⭐ {rating_a[0]} rated by {rating_a[1]} users" if rating_a else "New user (no ratings yet)"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Next Partner", callback_data="next")
    builder.button(text="Stop Chat", callback_data="stop")
    builder.adjust(2)
    
    await bot.send_message(user_a, msg_a, reply_markup=builder.as_markup())
    await bot.send_message(user_b, msg_b, reply_markup=builder.as_markup())


@router.message(Command("next"))
@router.callback_query(F.data == "next")
async def cmd_next(event):
    """Skip to next partner"""
    user_id = event.from_user.id
    message = event.message if hasattr(event, 'message') else event
    
    partner_id = await get_partner_id(user_id)
    
    if not partner_id:
        await message.answer("You're not in a chat. Use /find.")
        if isinstance(event, CallbackQuery):
            await event.answer()
        return
    
    # End chat atomically
    await end_chat_atomic(user_id, partner_id)
    
    # Update states: CHATTING → RATING
    await transition_state(user_id, UserState.CHATTING, UserState.RATING)
    await transition_state(partner_id, UserState.CHATTING, UserState.RATING)
    
    # Notify partner
    await message.bot.send_message(partner_id, "👋 Partner left the chat.")
    
    # Show rating prompts
    from handlers.rating import show_rating_prompt
    await show_rating_prompt(message.bot, user_id, partner_id)
    await show_rating_prompt(message.bot, partner_id, user_id)
    
    # Start new search: RATING → IDLE → SEARCHING
    await transition_state(user_id, UserState.RATING, UserState.IDLE)
    await start_matchmaking(message.bot, user_id)
    
    if isinstance(event, CallbackQuery):
        await event.answer()


@router.message(Command("stop"))
@router.callback_query(F.data == "stop")
async def cmd_stop(event):
    """Stop chatting"""
    user_id = event.from_user.id
    message = event.message if hasattr(event, 'message') else event
    
    state = await get_user_state(user_id)
    
    if state == UserState.CHATTING:
        partner_id = await get_partner_id(user_id)
        
        # End chat
        await end_chat_atomic(user_id, partner_id)
        
        # Update states
        await transition_state(user_id, UserState.CHATTING, UserState.RATING)
        await transition_state(partner_id, UserState.CHATTING, UserState.RATING)
        
        # Notify
        await message.bot.send_message(partner_id, "👋 Partner left the chat.")
        
        # Ratings
        from handlers.rating import show_rating_prompt
        await show_rating_prompt(message.bot, user_id, partner_id)
        await show_rating_prompt(message.bot, partner_id, user_id)
        
        # Back to idle
        await transition_state(user_id, UserState.RATING, UserState.IDLE)
        await message.answer("✅ Left chat. Use /find to start again.")
        
    elif state == UserState.SEARCHING:
        await leave_waiting_pool(user_id)
        await transition_state(user_id, UserState.SEARCHING, UserState.IDLE)
        await message.answer("✅ Search stopped.")
    
    if isinstance(event, CallbackQuery):
        await event.answer()
