"""
/how command - Feature explanations
NO SQL, pure informational content
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("how"))
async def cmd_how(message: Message):
    """Explain bot features"""
    text = (
        "🌻 Pairly Features Guide 🌻\n\n"
        
        "💰 SUNFLOWERS (Virtual Currency)\n"
        "Earn through:\n"
        "• Good ratings from chat partners\n"
        "• Daily activity streaks 🔥\n"
        "• Winning games 🎮\n"
        "• Gifts from other users\n\n"
        
        "🔥 STREAKS\n"
        "• Start after 3 consecutive days\n"
        "• 7-day streak: 1.5× sunflowers\n"
        "• 30-day streak: 2× sunflowers\n"
        "• Missing a day resets your streak\n"
        "• Use pets to protect your streak!\n\n"
        
        "🐾 PETS (Guardian Angels)\n"
        "• Protect you from losing streaks\n"
        "• Max 7 pets per user\n"
        "• Each pet saves one missed day\n"
        "• Types: Panda, Fox, Dog, Snake, Alligator, Dragon, Parrot\n"
        "• Premium users can buy anytime\n"
        "• Normal users: only during temp premium\n\n"
        
        "🎮 GAMES (Premium Only)\n"
        "• Tic Tac Toe\n"
        "• Word Chain (Easy/Hard)\n"
        "• Hangman\n"
        "• Bet sunflowers and win more!\n"
        "• Only playable during active chat\n"
        "• Leaving chat = automatic loss\n\n"
        
        "⭐ PREMIUM BENEFITS\n"
        "• Priority matching with high-rated users\n"
        "• Choose gender preference\n"
        "• Share up to 5 links per day\n"
        "• Create a Garden (levels 1-3)\n"
        "• Buy pets anytime\n"
        "• Better matching (less repeats)\n\n"
        
        "🌱 GARDEN (Premium Only)\n"
        "• Generates passive sunflowers\n"
        "• 3 levels: 20/40/60 🌻 per day\n"
        "• Keep your streak to maintain it\n"
        "• Downgrades if you miss a day\n"
        "• Destroyed if streak fully resets\n\n"
        
        "⏰ TEMPORARY PREMIUM\n"
        "• Buy 3-day premium with 1000 🌻\n"
        "• Once every 15 days\n"
        "• Access to games and pets\n"
        "• No garden creation\n\n"
        
        "Use /find to start chatting!"
    )
    
    await message.answer(text)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Show bot statistics"""
    from db.moderation import get_bot_stats
    
    stats = await get_bot_stats()
    
    text = (
        f"📊 Pairly Statistics\n\n"
        f"Total users: {stats['total_users']}\n"
        f"Premium users: {stats['premium_users']}\n"
        f"Active chats: {stats['active_chats']}\n"
        f"Searching: {stats['searching']}\n"
        f"Total ratings: {stats['total_ratings']}"
    )
    
    await message.answer(text)


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Show user profile"""
    from db.users import user_exists, get_user, is_premium, get_premium_days_remaining
    from db.sunflowers import get_sunflower_balance
    from db.ratings import get_average_rating
    from db.streaks import get_streak_days
    from db.pets import get_pets
    from db.gardens import get_garden
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    user_id = message.from_user.id
    
    if not await user_exists(user_id):
        await message.answer("Please use /start first.")
        return
    
    user = await get_user(user_id)
    balance = await get_sunflower_balance(user_id)
    rating_info = await get_average_rating(user_id)
    streak_days = await get_streak_days(user_id)
    pets = await get_pets(user_id)
    garden = await get_garden(user_id)
    
    # Build profile text
    gender = user['gender'].capitalize()
    
    # Premium status
    user_is_premium = await is_premium(user_id)
    if user_is_premium:
        days = await get_premium_days_remaining(user_id)
        premium_text = f"✨ Premium ({days} days left)"
    else:
        premium_text = "Free"
    
    # Rating
    if rating_info:
        rating_text = f"⭐ {rating_info[0]} ({rating_info[1]} ratings)"
    else:
        rating_text = "⭐ No ratings yet"
    
    # Streak
    if streak_days >= 30:
        streak_text = f"🔥 {streak_days} days (2× multiplier)"
    elif streak_days >= 7:
        streak_text = f"🔥 {streak_days} days (1.5× multiplier)"
    else:
        streak_text = f"🔥 {streak_days} days"
    
    # Sunflowers
    sf_text = (
        f"🌻 Total: {balance['total']}\n"
        f"  • Streak: {balance['streak']}\n"
        f"  • Games: {balance['game']}\n"
        f"  • Gifts: {balance['gift']}\n"
        f"  • Ratings: {balance['rating']}"
    )
    
    # Pets
    if pets:
        pet_texts = [f"{p[1]} (×{p[2]})" for p in pets]
        pet_text = f"🐾 Pets: {', '.join(pet_texts)}"
    else:
        pet_text = "🐾 No pets"
    
    # Garden
    if garden:
        garden_text = f"🌱 Garden: Level {garden[0]} ({garden[0] * 20} 🌻/day)"
    else:
        garden_text = "🌱 No garden"
    
    profile_text = (
        f"👤 Your Profile\n\n"
        f"Gender: {gender}\n"
        f"Status: {premium_text}\n"
        f"{rating_text}\n"
        f"{streak_text}\n\n"
        f"{sf_text}\n\n"
        f"{pet_text}\n"
        f"{garden_text}"
    )
    
    # Buttons
    builder = InlineKeyboardBuilder()
    
    if user_is_premium:
        builder.button(text="🐾 Buy Pet", callback_data="buy_pet_menu")
        
        from db.gardens import has_garden
        if not await has_garden(user_id):
            builder.button(text="🌱 Create Garden", callback_data="create_garden")
        else:
            builder.button(text="🌱 Harvest Garden", callback_data="harvest_garden")
    
    builder.adjust(1)
    
    await message.answer(profile_text, reply_markup=builder.as_markup())


@router.callback_query(lambda c: c.data == "buy_pet_menu")
async def buy_pet_menu(callback):
    """Show pet purchase menu"""
    from db.pets import get_pet_count
    from config import settings
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    
    user_id = callback.from_user.id
    
    count = await get_pet_count(user_id)
    if count >= settings.MAX_PETS:
        await callback.answer(f"You already have {settings.MAX_PETS} pets!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for pet_type in settings.PET_TYPES:
        builder.button(text=pet_type, callback_data=f"buy_pet:{pet_type}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "🐾 Choose a pet:\n\n"
        "Each pet saves your streak once.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data.startswith("buy_pet:"))
async def buy_pet(callback):
    """Purchase a pet"""
    from db.pets import add_pet
    
    pet_type = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    success = await add_pet(user_id, pet_type, 1)
    
    if success:
        await callback.message.edit_text(f"✅ You got a {pet_type}! 🐾")
    else:
        await callback.message.edit_text("❌ Failed to add pet. Maximum reached.")
    
    await callback.answer()


@router.callback_query(lambda c: c.data == "create_garden")
async def create_garden(callback):
    """Create a garden"""
    from db.gardens import create_garden as db_create_garden
    
    user_id = callback.from_user.id
    success = await db_create_garden(user_id)
    
    if success:
        await callback.message.edit_text(
            "🌱 Garden created!\n\n"
            "Level 1: Generates 20 🌻 per day\n\n"
            "Keep your streak to level up:\n"
            "• Level 2: 40 🌻/day\n"
            "• Level 3: 60 🌻/day\n\n"
            "⚠️ Missing a day downgrades your garden.\n"
            "Losing streak completely destroys it!"
        )
    else:
        await callback.message.edit_text("❌ Failed to create garden.")
    
    await callback.answer()


@router.callback_query(lambda c: c.data == "harvest_garden")
async def harvest_garden(callback):
    """Harvest garden"""
    from db.gardens import harvest_garden as db_harvest_garden
    
    user_id = callback.from_user.id
    reward = await db_harvest_garden(user_id)
    
    if reward:
        await callback.answer(f"Harvested {reward} 🌻!", show_alert=True)
    else:
        await callback.answer("Already harvested today!", show_alert=True)
