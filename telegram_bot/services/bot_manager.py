import asyncio
import logging
from typing import Dict

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import DJANGO_API_BASE_URL
from http_client import http_client
from handlers.personal import register_personal_bot_handlers

logger = logging.getLogger(__name__)

personal_bots: Dict[str, Bot] = {}
dispatchers: Dict[str, Dispatcher] = {}


async def create_personal_bot(token: str, chat_id: str) -> None:
    """Создать и запустить личного бота для пользователя"""
    try:
        bot = Bot(token=token, default=DefaultBotProperties(parse_mode=None))
        dp = Dispatcher()

        await register_personal_bot_handlers(dp, chat_id)

        personal_bots[chat_id] = bot
        dispatchers[chat_id] = dp

        asyncio.create_task(run_personal_bot_polling(dp, bot, chat_id))
        logger.info("Personal bot started for user %s", chat_id)
    except Exception as e:
        logger.error("Error creating personal bot for %s: %s", chat_id, e)


async def run_personal_bot_polling(dp: Dispatcher, bot: Bot, chat_id: str) -> None:
    """Запуск polling для личного бота"""
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error("Personal bot polling failed for %s: %s", chat_id, e)
        personal_bots.pop(chat_id, None)
        dispatchers.pop(chat_id, None)


async def initialize_existing_personal_bots() -> None:
    """Запускаем личных ботов для уже привязанных пользователей при старте"""
    try:
        users_url = f"{DJANGO_API_BASE_URL}/api/bot/get-users-with-personal-bots/"

        response = None
        last_exc: Exception | None = None
        for _ in range(5):
            try:
                response = await http_client.get(users_url)
                last_exc = None
                break
            except Exception as e:
                last_exc = e
                await asyncio.sleep(1)

        if response is None:
            raise last_exc or RuntimeError('Failed to fetch users with personal bots')

        if response.status_code == 200:
            users = response.json()
            logger.info("Found %s users with personal bots", len(users))
            for user in users:
                if user.get('personal_bot_token') and user.get('telegram_chat_id'):
                    logger.info("Starting personal bot for user %s", user.get('username'))
                    await create_personal_bot(user['personal_bot_token'], user['telegram_chat_id'])
        else:
            logger.warning("Failed to get users with personal bots: %s", response.status_code)

    except Exception as e:
        logger.error("Error initializing personal bots: %s", e)
