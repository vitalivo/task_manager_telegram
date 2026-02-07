import logging
from aiogram import types

from config import (
    API_ADMIN_CREATE_PROJECT,
    API_ADMIN_CREATE_TASK,
    API_PROJECT_SET_STATUS,
)
from http_client import http_client
from services.auth import ensure_linked, is_admin, parse_status_token

logger = logging.getLogger(__name__)


async def handle_admin_new_project(message: types.Message, chat_id: str, raw: str):
    if not await ensure_linked(message):
        return
    if not await is_admin(chat_id):
        await message.answer("❌ Недостаточно прав.")
        return

    parts = [p.strip() for p in (raw or '').split('|')]
    name = parts[0] if len(parts) > 0 and parts[0] else None
    client_name = parts[1] if len(parts) > 1 and parts[1] else None
    description = parts[2] if len(parts) > 2 and parts[2] else None

    if not name:
        await message.answer("Формат: /new_project Название | Клиент | Описание")
        return

    try:
        r = await http_client.post(API_ADMIN_CREATE_PROJECT, json={
            'chat_id': str(chat_id),
            'name': name,
            'client_name': client_name,
            'description': description,
            'source': 'telegram',
        })
        if r.status_code == 200:
            p = r.json().get('project')
            await message.answer(f"✅ Проект создан: #{p['id']} {p['name']}")
        else:
            await message.answer("❌ Не удалось создать проект.")
    except Exception as e:
        logger.error("Error in /new_project: %s", e)
        await message.answer("❌ Ошибка соединения. Попробуйте позже.")


async def handle_admin_new_task(message: types.Message, chat_id: str, raw: str):
    if not await ensure_linked(message):
        return
    if not await is_admin(chat_id):
        await message.answer("❌ Недостаточно прав.")
        return

    parts = [p.strip() for p in (raw or '').split('|')]
    if len(parts) < 2:
        await message.answer("Формат: /new_task project_id | Заголовок | username(опц.) | описание(опц.)")
        return

    project_id = parts[0]
    title = parts[1]
    assigned_to_username = parts[2] if len(parts) > 2 and parts[2] else None
    description = parts[3] if len(parts) > 3 and parts[3] else None

    try:
        r = await http_client.post(API_ADMIN_CREATE_TASK, json={
            'chat_id': str(chat_id),
            'project_id': str(project_id),
            'title': title,
            'assigned_to_username': assigned_to_username,
            'description': description,
        })
        if r.status_code == 200:
            t = r.json().get('task')
            await message.answer(f"✅ Задача создана: #{t['id']} {t['title']}")
        else:
            await message.answer("❌ Не удалось создать задачу.")
    except Exception as e:
        logger.error("Error in /new_task: %s", e)
        await message.answer("❌ Ошибка соединения. Попробуйте позже.")


async def handle_admin_project_status(message: types.Message, chat_id: str, project_id: str, status_token: str):
    if not await ensure_linked(message):
        return
    if not await is_admin(chat_id):
        await message.answer("❌ Недостаточно прав.")
        return

    new_status = parse_status_token(status_token)
    try:
        r = await http_client.post(API_PROJECT_SET_STATUS, json={
            'chat_id': str(chat_id),
            'project_id': str(project_id),
            'status': new_status,
        })
        if r.status_code == 200:
            await message.answer("✅ Статус проекта обновлён.")
        else:
            await message.answer("❌ Не удалось обновить статус проекта.")
    except Exception as e:
        logger.error("Error in /project_status: %s", e)
        await message.answer("❌ Ошибка соединения.")
