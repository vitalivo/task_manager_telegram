from aiogram import Dispatcher, types, F
from aiogram.filters import Command

from .tasks import (
    handle_tasks_command,
    handle_help_command,
    handle_today_command,
    handle_stats_command,
    handle_projects_command,
    handle_project_command,
    handle_task_command,
    handle_comment_command,
    handle_complete_task,
    handle_task_status_callback,
    handle_project_status_callback,
)
from .admin import (
    handle_admin_new_project,
    handle_admin_new_task,
    handle_admin_project_status,
)
from .linking import handle_login_link, handle_personal_off


async def register_personal_bot_handlers(dp: Dispatcher, user_chat_id: str):
    """Регистрируем хэндлеры для личного бота"""

    @dp.message(Command('tasks'))
    async def personal_tasks_handler(message: types.Message) -> None:
        await handle_tasks_command(message, user_chat_id)

    @dp.message(Command('help'))
    async def personal_help_handler(message: types.Message) -> None:
        await handle_help_command(message, user_chat_id)

    @dp.message(Command('today'))
    async def personal_today_handler(message: types.Message) -> None:
        await handle_today_command(message, user_chat_id)

    @dp.message(Command('stats'))
    async def personal_stats_handler(message: types.Message) -> None:
        await handle_stats_command(message, user_chat_id)

    @dp.message(Command('projects'))
    async def personal_projects_handler(message: types.Message) -> None:
        await handle_projects_command(message, user_chat_id)

    @dp.message(Command('project'))
    async def personal_project_handler(message: types.Message) -> None:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Формат: /project <id>")
            return
        await handle_project_command(message, user_chat_id, parts[1].strip())

    @dp.message(Command('task'))
    async def personal_task_handler(message: types.Message) -> None:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Формат: /task <id>")
            return
        await handle_task_command(message, user_chat_id, parts[1].strip())

    @dp.message(Command('comment'))
    async def personal_comment_handler(message: types.Message) -> None:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("Формат: /comment <task_id> <текст>")
            return
        await handle_comment_command(message, user_chat_id, parts[1].strip(), parts[2].strip())

    @dp.message(Command('login'))
    async def personal_login_handler(message: types.Message) -> None:
        await handle_login_link(message, user_chat_id)

    @dp.message(Command('personal_off'))
    async def personal_off_handler(message: types.Message) -> None:
        await handle_personal_off(message, user_chat_id)

    @dp.message(Command('new_project'))
    async def personal_new_project_handler(message: types.Message) -> None:
        raw = message.text[len('/new_project'):].strip()
        await handle_admin_new_project(message, user_chat_id, raw)

    @dp.message(Command('new_task'))
    async def personal_new_task_handler(message: types.Message) -> None:
        raw = message.text[len('/new_task'):].strip()
        await handle_admin_new_task(message, user_chat_id, raw)

    @dp.message(Command('project_status'))
    async def personal_project_status_handler(message: types.Message) -> None:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("Формат: /project_status <project_id> <статус>")
            return
        await handle_admin_project_status(message, user_chat_id, parts[1].strip(), parts[2].strip())

    @dp.callback_query(F.data.startswith("complete_"))
    async def personal_complete_handler(callback: types.CallbackQuery):
        await handle_complete_task(callback, user_chat_id)

    @dp.callback_query(F.data.startswith("task_"))
    async def personal_task_open_handler(callback: types.CallbackQuery):
        task_id = callback.data.split('_', 1)[1]
        await handle_task_command(callback.message, user_chat_id, task_id)
        await callback.answer()

    @dp.callback_query(F.data.startswith("proj_"))
    async def personal_project_open_handler(callback: types.CallbackQuery):
        project_id = callback.data.split('_', 1)[1]
        await handle_project_command(callback.message, user_chat_id, project_id)
        await callback.answer()

    @dp.callback_query(F.data.startswith("tstatus_"))
    async def personal_task_status_handler(callback: types.CallbackQuery):
        _, task_id, st = callback.data.split('_', 2)
        await handle_task_status_callback(callback, user_chat_id, task_id, st)

    @dp.callback_query(F.data.startswith("pstatus_"))
    async def personal_project_status_cb_handler(callback: types.CallbackQuery):
        _, project_id, st = callback.data.split('_', 2)
        await handle_project_status_callback(callback, user_chat_id, project_id, st)
