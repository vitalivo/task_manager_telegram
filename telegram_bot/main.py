import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import SYSTEM_BOT_TOKEN
from handlers.system import register_system_bot_handlers
from services.bot_manager import initialize_existing_personal_bots
from http_client import http_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


auto_system_bot: Bot | None = None


async def main() -> None:
    """Основная функция запуска"""
    global auto_system_bot

    if not SYSTEM_BOT_TOKEN:
        raise RuntimeError("SYSTEM_BOT_TOKEN is not set")

    auto_system_bot = Bot(token=SYSTEM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
    system_dp = Dispatcher()

    await register_system_bot_handlers(system_dp)

    logger.info("Initializing existing personal bots...")
    await initialize_existing_personal_bots()

    logger.info("Starting system bot...")
    await system_dp.start_polling(auto_system_bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
    finally:
        try:
            asyncio.run(http_client.aclose())
        except RuntimeError:
            # event loop already closed
            pass
