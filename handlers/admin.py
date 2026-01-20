"""
Admin panel handlers - NO SQL, uses db.moderation
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import settings
from db.moderation import (
    get_bot_stats, get_recent_messages, ban_user, unban_user, get_all_user_ids
)

router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id == settings.ADMIN_ID


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin panel"""
    if not is_admin(message.from_user.id):
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Statistics", callback_data="admin_stats")
    builder.button(text="👁️ Recent Messages", callback_data="admin_messages")
    builder.adjust(2)
    
    await message.answer(
        "🔐 Admin Panel\n\nSelect an action:",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Show detailed statistics"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Unauthorized", show_alert=True)
        return
    
    stats = await get_bot_stats()
    
    text = (
        f"📊 Bot Statistics\n\n"
        f"👥 Total Users: {stats['total_users']}\n"
        f"⭐ Premium Users: {stats['premium_users']}\n"
        f"💬 Active Chats: {stats['active_chats']}\n"
        f"🔍 Searching: {stats['searching']}\n"
        f"⭐ Total Ratings: {stats['total_ratings']}\n"
        f"🚫 Banned Users: {stats['banned_users']}"
    )
    
    await callback.message.edit_text(text)
    await callback.answer()


@router.callback_query(F.data == "admin_messages")
async def admin_messages(callback: CallbackQuery):
    """Show recent monitored messages"""
    if not is_admin(callback.from_user.id):
        await callback.answer("Unauthorized", show_alert=True)
        return
    
    messages = await get_recent_messages(20)
    
    if not messages:
        await callback.message.edit_text("No recent messages.")
        await callback.answer()
        return
    
    text = "👁️ Recent Messages\n\n"
    
    for msg in messages[:20]:
        timestamp = msg['sent_at'][:19] if msg['sent_at'] else "unknown"
        
        if msg['message_type'] == 'text':
            content = msg['content'][:50] + "..." if msg['content'] and len(msg['content']) > 50 else msg['content']
            text += f"User {msg['sender_id']} ({timestamp}):\n{content}\n\n"
        else:
            text += f"User {msg['sender_id']} ({timestamp}): [{msg['message_type']}]\n\n"
        
        if len(text) > 3000:
            break
    
    await callback.message.edit_text(text)
    await callback.answer()


@router.message(Command("ban"))
async def cmd_ban(message: Message):
    """Ban a user"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split(maxsplit=3)
        if len(parts) < 4:
            await message.answer("Usage: /ban <user_id> <hours> <reason>")
            return
        
        user_id = int(parts[1])
        hours = int(parts[2])
        reason = parts[3]
        
        await ban_user(user_id, hours, reason)
        
        await message.answer(
            f"✅ User {user_id} banned for {hours} hours.\n"
            f"Reason: {reason}"
        )
        
        # Notify user
        try:
            await message.bot.send_message(
                user_id,
                f"🚫 You have been banned for {hours} hours.\n\n"
                f"Reason: {reason}"
            )
        except:
            pass
    
    except (ValueError, IndexError):
        await message.answer("Invalid format. Usage: /ban <user_id> <hours> <reason>")


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    """Unban a user"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Usage: /unban <user_id>")
            return
        
        user_id = int(parts[1])
        await unban_user(user_id)
        
        await message.answer(f"✅ User {user_id} unbanned.")
        
        # Notify user
        try:
            await message.bot.send_message(
                user_id,
                "✅ You have been unbanned. You can use the bot again."
            )
        except:
            pass
    
    except ValueError:
        await message.answer("Invalid user ID.")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    """Broadcast message to all users"""
    if not is_admin(message.from_user.id):
        return
    
    text = message.text.replace("/broadcast", "", 1).strip()
    
    if not text:
        await message.answer("Usage: /broadcast <message>")
        return
    
    users = await get_all_user_ids()
    
    success = 0
    failed = 0
    
    status_msg = await message.answer(f"Broadcasting to {len(users)} users...")
    
    for user_id in users:
        try:
            await message.bot.send_message(user_id, f"📢 Announcement:\n\n{text}")
            success += 1
        except:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ Broadcast complete!\n\n"
        f"Sent: {success}\n"
        f"Failed: {failed}"
    )


@router.message(Command("premium"))
async def cmd_premium(message: Message):
    """Show/buy premium"""
    from aiogram.types import LabeledPrice, PreCheckoutQuery
    from db.users import user_exists, is_premium, get_premium_days_remaining
    from services.premium import get_premium_plans, can_buy_temp_premium_check, buy_temp_premium
    from db.sunflowers import get_sunflower_balance
    
    user_id = message.from_user.id
    
    if not await user_exists(user_id):
        await message.answer("Please use /start first.")
        return
    
    # Check current status
    user_is_premium = await is_premium(user_id)
    
    if user_is_premium:
        days_left = await get_premium_days_remaining(user_id)
        await message.answer(
            f"✨ You are a Premium member!\n\n"
            f"Days remaining: {days_left}\n\n"
            "Premium Benefits:\n"
            "• Priority matching\n"
            "• Gender preference\n"
            "• 5 links per day\n"
            "• Garden creation\n"
            "• Buy pets anytime\n"
            "• Fewer repeat matches"
        )
        return
    
    # Show purchase options
    text = (
        "⭐ Become Premium! ⭐\n\n"
        "Benefits:\n"
        "• Priority matching with high-rated users\n"
        "• Choose gender preference\n"
        "• Share up to 5 links/day\n"
        "• Create Garden (passive sunflowers)\n"
        "• Buy pets anytime\n"
        "• Better matching\n\n"
        "Select a plan:"
    )
    
    builder = InlineKeyboardBuilder()
    
    plans = get_premium_plans()
    for plan in plans:
        bonus_text = f" (+{plan['bonus']}d)" if plan['bonus'] > 0 else ""
        builder.button(
            text=f"{plan['duration']} days - {plan['price']} ⭐{bonus_text}",
            callback_data=f"buy_premium:{plan['duration']}"
        )
    
    # Add temp premium option
    can_buy, reason = await can_buy_temp_premium_check(user_id)
    if can_buy:
        from config import settings as cfg
        builder.button(
            text=f"🌻 3-day temp ({cfg.TEMP_PREMIUM_COST} sunflowers)",
            callback_data="buy_temp_premium"
        )
    
    builder.adjust(1)
    
    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("buy_premium:"))
async def buy_premium_callback(callback: CallbackQuery):
    """Handle premium purchase via Telegram Stars"""
    from aiogram.types import LabeledPrice
    from services.premium import get_plan_by_duration
    
    duration = int(callback.data.split(":")[1])
    plan = get_plan_by_duration(duration)
    
    if not plan:
        await callback.answer("Invalid plan", show_alert=True)
        return
    
    # Create invoice
    title = f"Pairly Premium - {duration} days"
    description = f"Premium subscription for {plan['actual_days']} days"
    payload = f"premium_{duration}_{callback.from_user.id}"
    
    prices = [LabeledPrice(label="Premium", amount=plan['price'])]
    
    try:
        await callback.message.answer_invoice(
            title=title,
            description=description,
            payload=payload,
            provider_token="",  # Empty for Telegram Stars
            currency="XTR",
            prices=prices
        )
        await callback.answer()
    except Exception as e:
        await callback.answer("Failed to create invoice", show_alert=True)


@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query):
    """Handle pre-checkout"""
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """Handle successful payment"""
    from services.premium import activate_premium, get_plan_by_duration
    
    payload = message.successful_payment.invoice_payload
    parts = payload.split("_")
    
    if parts[0] == "premium":
        duration = int(parts[1])
        user_id = int(parts[2])
        
        plan = get_plan_by_duration(duration)
        if plan:
            await activate_premium(user_id, plan['actual_days'])
            
            await message.answer(
                f"✨ Premium activated for {plan['actual_days']} days!\n\n"
                "Enjoy your premium benefits!"
            )


@router.callback_query(F.data == "buy_temp_premium")
async def buy_temp_premium_callback(callback: CallbackQuery):
    """Handle temp premium purchase"""
    from services.premium import buy_temp_premium as service_buy_temp_premium
    from config import settings as cfg
    
    user_id = callback.from_user.id
    
    success = await service_buy_temp_premium(user_id)
    
    if success:
        await callback.message.edit_text(
            f"✨ Temporary Premium activated for {cfg.TEMP_PREMIUM_DAYS} days!\n\n"
            "You can now:\n"
            "• Buy pets\n"
            "• Play games\n"
            "• Use premium features\n\n"
            "Note: Garden creation requires full premium."
        )
    else:
        await callback.message.edit_text("❌ Failed to activate temp premium.")
    
    await callback.answer()
