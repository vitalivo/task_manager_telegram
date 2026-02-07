import logging
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
import httpx

from config import API_LINK_ACCOUNT, API_WEB_LOGIN_TOKEN, API_CLEAR_PERSONAL_BOT
from http_client import http_client
from services.auth import ensure_linked, get_user_bot_token

logger = logging.getLogger(__name__)


async def handle_login_link(message: types.Message, chat_id: str) -> None:
    if not await ensure_linked(message):
        return
    try:
        r = await http_client.post(API_WEB_LOGIN_TOKEN, json={'chat_id': str(chat_id)})
        if r.status_code != 200:
            await message.answer("❌ Не удалось создать ссылку входа. Попробуйте позже.")
            return

        data = r.json()
        login_url = data.get('login_url')
        expires_in = data.get('expires_in')

        kb = InlineKeyboardBuilder()
        if login_url:
            kb.button(text='Войти в веб', url=login_url)

        ttl_text = f" (действует {int(expires_in)} сек.)" if expires_in else ""
        await message.answer(
            f"🔐 Ссылка для входа в веб{ttl_text}:",
            reply_markup=kb.as_markup() if login_url else None,
        )
        if login_url:
            await message.answer(login_url)
    except Exception as e:
        logger.error("Error creating web login link: %s", e)
        await message.answer("❌ Ошибка соединения. Попробуйте позже.")


async def handle_personal_off(message: types.Message, chat_id: str) -> None:
    if not await ensure_linked(message):
        return
    try:
        r = await http_client.post(API_CLEAR_PERSONAL_BOT, json={'chat_id': str(chat_id)})
        if r.status_code == 200:
            await message.answer("✅ Личный бот отключён. Теперь можно пользоваться системным ботом.")
        else:
            await message.answer("❌ Не удалось отключить личного бота. Попробуйте позже.")
    except Exception as e:
        logger.error("Error clearing personal bot: %s", e)
        await message.answer("❌ Ошибка соединения. Попробуйте позже.")


async def handle_account_linking(message: types.Message, token: str, chat_id: str):
    """Обработчик привязки аккаунта"""
    try:
        response = await http_client.post(
            API_LINK_ACCOUNT, 
            json={"token": token, "chat_id": chat_id}
        )
        
        if response.status_code == 200:
            username = response.json().get('username', 'пользователь')
            
            personal_token = await get_user_bot_token(chat_id)
            if personal_token:
                # локальный импорт, чтобы избежать циклов
                from services.bot_manager import create_personal_bot
                await create_personal_bot(personal_token, chat_id)
                await message.answer(
                    f"✅ Аккаунт успешно привязан! Добро пожаловать, {username}.\n\n"
                    f"🤖 Ваш личный бот активирован! Теперь используйте его для управления задачами."
                )
            else:
                await message.answer(
                    f"✅ Аккаунт успешно привязан! Добро пожаловать, {username}.\n\n"
                    f"📋 Используйте команду /tasks для просмотра ваших задач."
                )
        else:
            await message.answer("❌ Ошибка привязки. Неверный токен или токен уже использован.")
            
    except httpx.HTTPError as e:
        logger.error("HTTP error in account linking: %s", e)
        await message.answer("❌ Ошибка соединения с сервером.")
