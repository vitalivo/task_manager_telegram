import logging
import html
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
import httpx

from config import (
    API_GET_TASKS,
    API_COMPLETE_TASK,
    API_TODAY,
    API_PROJECTS,
    API_PROJECT_DETAIL,
    API_TASK_DETAIL,
    API_TASK_SET_STATUS,
    API_PROJECT_SET_STATUS,
    API_TASK_COMMENT,
    API_TASK_STATS,
)
from http_client import http_client
from services.auth import ensure_linked, is_admin

logger = logging.getLogger(__name__)


async def handle_tasks_command(message: types.Message, chat_id: str):
    """Общий обработчик команды /tasks"""
    try:
        response = await http_client.get(API_GET_TASKS, params={"chat_id": str(chat_id)})
        
        if response.status_code == 404:
            await message.answer("❌ Ваш аккаунт не привязан. Используйте токен из веб-приложения, чтобы привязать его.")
            return

        tasks = response.json()
        
        if not tasks:
            await message.answer("🎉 У вас нет активных задач!")
            return

        builder = InlineKeyboardBuilder()
        text = "🎯 Ваши текущие задачи:\n\n"
        
        for task in tasks:
            due_date = f"Срок: {task['due_date'].split('T')[0]}" if task.get('due_date') else "Срок: Не установлен"
            status_display = task.get('status_display') or task.get('status') or ''
            title = html.escape(str(task.get('title') or ''))
            list_name = html.escape(str(task.get('list_name') or ''))
            status_text = html.escape(str(status_display))
            text += (
                f"ID:{task['id']} - <b>{title}</b>\n"
                f"<i>{due_date} (проект: {list_name})</i>\n"
                f"Статус: {status_text}\n\n"
            )
            builder.button(text=f"📌 Открыть #{task['id']}", callback_data=f"task_{task['id']}")
            builder.button(text=f"✅ Выполнить #{task['id']}", callback_data=f"complete_{task['id']}")
            
        builder.adjust(1)
        
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode='HTML')

    except httpx.HTTPError as e:
        logger.error("HTTP error in tasks command: %s", e)
        await message.answer("❌ Ошибка соединения с сервером.")


async def handle_complete_task(callback: types.CallbackQuery, chat_id: str):
    """Общий обработчик выполнения задач"""
    task_id = callback.data.split("_")[1]
    
    try:
        response = await http_client.post(
            API_COMPLETE_TASK, 
            json={"chat_id": str(chat_id), "task_id": task_id}
        )
        
        if response.status_code == 200:
            await callback.answer(f"✅ Задача #{task_id} отмечена как выполненная!", show_alert=True)
            await callback.message.edit_text(
                f"{callback.message.text}\n\n-- Задача #{task_id} выполнена --",
                reply_markup=None
            )
        else:
            await callback.answer("❌ Не удалось завершить задачу. Возможно, она уже выполнена или не найдена.", show_alert=True)

    except httpx.HTTPError as e:
        logger.error("HTTP error in complete task: %s", e)
        await callback.answer("❌ Ошибка соединения с сервером.", show_alert=True)


async def handle_help_command(message: types.Message, chat_id: str):
    if not await ensure_linked(message):
        return

    admin_flag = await is_admin(chat_id)
    base = (
        "Команды:\n"
        "• /tasks — мои задачи\n"
        "• /today — задачи на сегодня\n"
        "• /stats — статистика задач\n"
        "• /task <id> — карточка задачи\n"
        "• /comment <task_id> <текст> — комментарий к задаче\n"
        "• /projects — мои проекты\n"
        "• /project <id> — карточка проекта\n"
    )
    if admin_flag:
        base += (
            "\nАдмин/менеджер:\n"
            "• /new_project <Название | Клиент | Описание>\n"
            "• /new_task <project_id | Заголовок | username(опц.) | описание(опц.)>\n"
            "• /project_status <project_id> <статус> (переписка/разработка/непринят/готово)\n"
        )

    await message.answer(base)


async def handle_today_command(message: types.Message, chat_id: str):
    if not await ensure_linked(message):
        return
    try:
        r = await http_client.get(API_TODAY, params={'chat_id': str(chat_id)})
        if r.status_code != 200:
            await message.answer("❌ Не удалось получить задачи на сегодня.")
            return
        tasks = r.json()
        if not tasks:
            await message.answer("🎉 На сегодня задач нет!")
            return
        text = "🗓 Задачи на сегодня:\n\n"
        for t in tasks:
            status_display = t.get('status_display') or t.get('status')
            due_date = t.get('due_date')
            due = due_date.split('T')[0] if due_date else '—'
            text += f"#{t['id']} • {t['title']} • {status_display} • {due} (проект: {t.get('list_name')})\n"
        await message.answer(text)
    except Exception as e:
        logger.error("Error in /today: %s", e)
        await message.answer("❌ Ошибка соединения с сервером.")


async def handle_projects_command(message: types.Message, chat_id: str):
    if not await ensure_linked(message):
        return
    try:
        r = await http_client.get(API_PROJECTS, params={'chat_id': str(chat_id)})
        if r.status_code != 200:
            await message.answer("❌ Не удалось получить проекты.")
            return
        projects = r.json()
        if not projects:
            await message.answer("Проектов пока нет.")
            return

        builder = InlineKeyboardBuilder()
        text = "📁 Ваши проекты:\n\n"
        for p in projects[:20]:
            status_display = p.get('status_display') or p.get('status')
            client = (p.get('client') or {}).get('name') if p.get('client') else None
            client_text = f" • {client}" if client else ""
            text += f"#{p['id']} • {p['name']} • {status_display}{client_text}\n"
            builder.button(text=f"📌 Проект #{p['id']}", callback_data=f"proj_{p['id']}")
        builder.adjust(1)
        await message.answer(text, reply_markup=builder.as_markup())
    except Exception as e:
        logger.error("Error in /projects: %s", e)
        await message.answer("❌ Ошибка соединения с сервером.")


async def handle_stats_command(message: types.Message, chat_id: str):
    if not await ensure_linked(message):
        return
    try:
        r = await http_client.get(API_TASK_STATS, params={'chat_id': str(chat_id)})
        if r.status_code != 200:
            await message.answer("❌ Не удалось получить статистику.")
            return
        data = r.json()
        total = data.get('total', 0)
        by_status = data.get('by_status') or []
        lines = [f"📊 Всего задач: {total}"]
        for item in by_status:
            lines.append(f"• {item.get('status')}: {item.get('count')}")
        await message.answer("\n".join(lines))
    except Exception as e:
        logger.error("Error in /stats: %s", e)
        await message.answer("❌ Ошибка соединения с сервером.")


async def handle_project_command(message: types.Message, chat_id: str, project_id: str):
    if not await ensure_linked(message):
        return
    try:
        r = await http_client.get(API_PROJECT_DETAIL, params={'chat_id': str(chat_id), 'project_id': str(project_id)})
        if r.status_code != 200:
            await message.answer("❌ Проект не найден или нет доступа.")
            return
        p = r.json()
        status_display = p.get('status_display') or p.get('status')
        source_display = p.get('source_display') or p.get('source')
        client = (p.get('client') or {}).get('name') if p.get('client') else '—'
        text = (
            f"📌 Проект #{p['id']}: {p['name']}\n"
            f"Статус: {status_display}\n"
            f"Источник: {source_display or '—'}\n"
            f"Клиент: {client}\n"
            f"Цена: {p.get('price') or '—'}\n"
            f"Дедлайн: {p.get('deadline') or '—'}\n\n"
            f"Описание: {p.get('description') or '—'}"
        )

        builder = InlineKeyboardBuilder()
        if await is_admin(chat_id):
            builder.button(text="🟦 Переписка", callback_data=f"pstatus_{p['id']}_negotiation")
            builder.button(text="🟨 В разработке", callback_data=f"pstatus_{p['id']}_development")
            builder.button(text="🟥 Не принят", callback_data=f"pstatus_{p['id']}_rejected")
            builder.button(text="🟩 Завершён", callback_data=f"pstatus_{p['id']}_done")
            builder.adjust(2)
            await message.answer(text, reply_markup=builder.as_markup())
        else:
            await message.answer(text)
    except Exception as e:
        logger.error("Error in /project: %s", e)
        await message.answer("❌ Ошибка соединения с сервером.")


async def handle_task_command(message: types.Message, chat_id: str, task_id: str):
    if not await ensure_linked(message):
        return
    try:
        r = await http_client.get(API_TASK_DETAIL, params={'chat_id': str(chat_id), 'task_id': str(task_id)})
        if r.status_code != 200:
            await message.answer("❌ Задача не найдена или нет доступа.")
            return
        payload = r.json()
        t = payload.get('task') or {}
        comments = payload.get('comments') or []

        status_display = t.get('status_display') or t.get('status')
        priority_display = t.get('priority_display') or t.get('priority')
        due = t.get('due_date')
        due_text = due.split('T')[0] if due else '—'
        text = (
            f"📝 Задача #{t.get('id')}: {t.get('title')}\n"
            f"Проект: {t.get('list_name')}\n"
            f"Статус: {status_display}\n"
            f"Приоритет: {priority_display}\n"
            f"Срок: {due_text}\n\n"
            f"Описание: {t.get('description') or '—'}\n"
        )
        if comments:
            last = comments[0]
            text += f"\nПоследний комментарий: {last.get('author_username') or '—'}: {last.get('text')}"

        builder = InlineKeyboardBuilder()
        builder.button(text="🆕 Новая", callback_data=f"tstatus_{t.get('id')}_new")
        builder.button(text="🏗 В работе", callback_data=f"tstatus_{t.get('id')}_in_progress")
        builder.button(text="🔎 Проверка", callback_data=f"tstatus_{t.get('id')}_review")
        builder.button(text="✅ Готово", callback_data=f"tstatus_{t.get('id')}_done")
        builder.adjust(2)
        await message.answer(text, reply_markup=builder.as_markup())
    except Exception as e:
        logger.error("Error in /task: %s", e)
        await message.answer("❌ Ошибка соединения с сервером.")


async def handle_comment_command(message: types.Message, chat_id: str, task_id: str, text: str):
    if not await ensure_linked(message):
        return
    try:
        r = await http_client.post(API_TASK_COMMENT, json={'chat_id': str(chat_id), 'task_id': str(task_id), 'text': str(text)})
        if r.status_code == 200:
            await message.answer("✅ Комментарий добавлен.")
        else:
            await message.answer("❌ Не удалось добавить комментарий.")
    except Exception as e:
        logger.error("Error in /comment: %s", e)
        await message.answer("❌ Ошибка соединения с сервером.")


async def handle_task_status_callback(callback: types.CallbackQuery, chat_id: str, task_id: str, status: str):
    try:
        r = await http_client.post(API_TASK_SET_STATUS, json={
            'chat_id': str(chat_id),
            'task_id': task_id,
            'status': status,
        })
        if r.status_code == 200:
            await callback.answer("✅ Статус обновлён", show_alert=False)
        else:
            await callback.answer("❌ Нет доступа/ошибка", show_alert=True)
    except Exception as e:
        logger.error("Error setting task status: %s", e)
        await callback.answer("❌ Ошибка соединения", show_alert=True)


async def handle_project_status_callback(callback: types.CallbackQuery, chat_id: str, project_id: str, status: str):
    try:
        r = await http_client.post(API_PROJECT_SET_STATUS, json={
            'chat_id': str(chat_id),
            'project_id': project_id,
            'status': status,
        })
        if r.status_code == 200:
            await callback.answer("✅ Статус проекта обновлён", show_alert=False)
        else:
            await callback.answer("❌ Нет доступа/ошибка", show_alert=True)
    except Exception as e:
        logger.error("Error setting project status: %s", e)
        await callback.answer("❌ Ошибка соединения", show_alert=True)
