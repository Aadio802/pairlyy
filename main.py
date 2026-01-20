"""
Pairly - Production Anonymous Chat Bot (HARDENED V2)
Main Entry Point - ALL HANDLERS REGISTERED
"""
import asyncio
import sys
import logging
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

from config import settings
from db.connection import init_database
from db.moderation import is_banned
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============ MIDDLEWARE ============
class BanCheckMiddleware(BaseMiddleware):
    """Check if user is banned before processing"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        ban_info = await is_banned(user_id)
        
        if ban_info:
            banned_until, reason = ban_info
            hours_left = int((banned_until - datetime.now()).total_seconds() / 3600)
            
            ban_msg = (
                f"🚫 You are banned\n\n"
                f"Reason: {reason}\n"
                f"Time remaining: {hours_left} hours"
            )
            
            if isinstance(event, Message):
                await event.answer(ban_msg)
            else:
                await event.answer(ban_msg, show_alert=True)
            
            return
        
        return await handler(event, data)


async def main():
    """Initialize and start bot"""
    logger.info("=" * 50)
    logger.info("Starting Pairly bot (HARDENED V2)...")
    logger.info("=" * 50)
    
    # Validate configuration
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN not set in environment variables")
        sys.exit(1)
    
    if not settings.ADMIN_ID:
        logger.error("ADMIN_ID not set in environment variables")
        sys.exit(1)
    
    logger.info(f"Admin ID: {settings.ADMIN_ID}")
    
    try:
        # Initialize database with WAL mode
        await init_database()
        logger.info("Database initialized with WAL mode")
        
        # Initialize bot
        bot = Bot(token=settings.BOT_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Setup middleware
        dp.message.middleware(BanCheckMiddleware())
        dp.callback_query.middleware(BanCheckMiddleware())
        logger.info("Middleware configured")
        
        # Register ALL handlers
        from handlers.start import router as start_router
        from handlers.matchmaking import router as matchmaking_router
        from handlers.rating import router as rating_router
        from handlers.how import router as how_router
        from handlers.admin import router as admin_router
        from handlers.games import router as games_router
        
        dp.include_router(start_router)
        dp.include_router(matchmaking_router)
        dp.include_router(rating_router)
        dp.include_router(how_router)
        dp.include_router(admin_router)
        dp.include_router(games_router)
        
        logger.info("All handlers registered (6 routers)")
        
        # Get bot info
        bot_info = await bot.get_me()
        logger.info(f"Bot username: @{bot_info.username}")
        logger.info(f"Bot name: {bot_info.first_name}")
        
        logger.info("=" * 50)
        logger.info("✅ Bot started successfully!")
        logger.info("✅ All systems operational")
        logger.info("=" * 50)
        
        # Start polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error: {type(e).__name__}: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        try:
            await bot.session.close()
            logger.info("Bot session closed")
        except:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped.")
