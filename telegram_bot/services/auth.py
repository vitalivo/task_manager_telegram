import logging
from typing import Optional

from aiogram import types

from config import API_ME, API_GET_USER_BOT_TOKEN
from http_client import http_client

logger = logging.getLogger(__name__)


def parse_status_token(token: str) -> str:
    t = (token or '').strip().lower()
    mapping = {
        # Проекты
        'переписка': 'negotiation',
        'переговоры': 'negotiation',
        'разработка': 'development',
        'вразработке': 'development',
        'непринят': 'rejected',
        'не принят': 'rejected',
        'отказ': 'rejected',
        'завершен': 'done',
        'завершён': 'done',
        'готово': 'done',
        'done': 'done',
        'development': 'development',
        'negotiation': 'negotiation',
        'rejected': 'rejected',
        # Задачи
        'новая': 'new',
        'new': 'new',
        'вработе': 'in_progress',
        'в работе': 'in_progress',
        'in_progress': 'in_progress',
        'проверка': 'review',
        'на проверке': 'review',
        'review': 'review',
    }
    return mapping.get(t, t)


async def is_admin(chat_id: str) -> bool:
    try:
        r = await http_client.get(API_ME, params={'chat_id': str(chat_id)})
        if r.status_code == 200:
            return bool(r.json().get('is_admin'))
    except Exception as e:
        logger.error("Error checking admin role: %s", e)
    return False


async def ensure_linked(message: types.Message) -> bool:
    """Проверка привязки аккаунта для команд (кроме /start)."""
    chat_id = str(message.chat.id)
    try:
        r = await http_client.get(API_ME, params={'chat_id': chat_id})
        if r.status_code == 200 and r.json().get('linked'):
            return True
    except Exception:
        pass
    await message.answer("❌ Аккаунт не привязан. Откройте веб-приложение и привяжите через /start <токен>.")
    return False


async def get_user_bot_token(chat_id: str) -> Optional[str]:
    """Получить токен личного бота пользователя из Django API"""
    try:
        response = await http_client.get(
            API_GET_USER_BOT_TOKEN,
            params={"chat_id": chat_id}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('personal_bot_token')
    except Exception as e:
        logger.error("Error getting user bot token for %s: %s", chat_id, e)
    return None
