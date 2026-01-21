print("BOOT: main.py loaded")

import asyncio
import sys
import logging
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from datetime import datetime

from config import settings
from db.connection import init_database
from db.moderation import is_banned

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============ MIDDLEWARE ============
class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
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
    print("BOOT: inside main()")

    # Validate config
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN not set")
        sys.exit(1)

    if not settings.ADMIN_ID:
        logger.error("ADMIN_ID not set")
        sys.exit(1)

    # Init database
    print("BOOT: calling init_database()")
    await init_database()
    print("BOOT: database ready")

    # Init bot
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Middleware
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())

    # Routers
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

    logger.info("All handlers registered")

    me = await bot.get_me()
    logger.info(f"Bot online: @{me.username}")

    print("BOT IS ALIVE")

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
