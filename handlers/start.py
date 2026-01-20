"""
Start command handler - NO SQL, uses db modules
"""
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db.users import user_exists, create_user, transition_state, UserState

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    
    # Check if user exists
    if await user_exists(user_id):
        # Existing user - behave like /find
        from handlers.matchmaking import cmd_find
        await cmd_find(message)
        return
    
    # New user - show welcome
    welcome_text = (
        "🌻 Welcome to Pairly! 🌻\n\n"
        "Anonymous chatting with strangers\n\n"
        "⚠️ Important:\n"
        "• You may encounter unfiltered content\n"
        "• All chats are monitored for safety\n"
        "• Premium users get priority matching\n"
        "• Earn Sunflowers 🌻 through:\n"
        "  - Maintaining streaks 🔥\n"
        "  - Winning games 🎮\n"
        "  - Good ratings ⭐\n"
        "  - Gifts from others\n\n"
        "By using /find or /next, you agree to these terms.\n\n"
        "First, select your gender:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Male", callback_data="gender:male")
    builder.button(text="Female", callback_data="gender:female")
    builder.adjust(2)
    
    await message.answer(welcome_text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("gender:"))
async def select_gender(callback: CallbackQuery):
    """Handle gender selection"""
    user_id = callback.from_user.id
    gender = callback.data.split(":")[1]
    
    # Create user
    await create_user(user_id, gender)
    
    # Transition: NEW → AGREED → IDLE
    await transition_state(user_id, UserState.NEW, UserState.AGREED)
    await transition_state(user_id, UserState.AGREED, UserState.IDLE)
    
    await callback.message.edit_text(
        f"✅ Gender set to: {gender.capitalize()}\n\n"
        "Ready to chat! Use /find to start.\n\n"
        "Commands:\n"
        "/find - Find a partner\n"
        "/next - Skip partner\n"
        "/stop - Leave chat\n"
        "/how - Learn features"
    )
    
    await callback.answer()
