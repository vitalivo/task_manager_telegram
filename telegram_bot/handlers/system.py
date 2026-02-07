from aiogram import Dispatcher, types, F
from aiogram.filters import CommandStart, Command

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
from .linking import (
    handle_account_linking,
    handle_login_link,
    handle_personal_off,
)
from services.auth import get_user_bot_token


async def register_system_bot_handlers(dp: Dispatcher):
    """Регистрируем хэндлеры для системного бота"""

    @dp.message(CommandStart())
    async def system_command_start_handler(message: types.Message) -> None:
        args = message.text.split()
        chat_id = str(message.chat.id)

        if len(args) > 1:
            token = args[1]
            await handle_account_linking(message, token, chat_id)
        else:
            await message.answer(
                "👋 Привет! Я бот для управления задачами.\n\n"
                "Чтобы начать, привяжите свой аккаунт, используя токен из веб-приложения.\n\n"
                "После привязки вы можете:\n"
                "• Просматривать задачи командой /tasks\n"
                "• Отмечать задачи выполненными\n"
                "\nСправка: /help"
            )

    @dp.message(Command('help'))
    async def system_help_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer("🤖 Используйте вашего личного бота для работы с задачами/проектами.")
            return
        await handle_help_command(message, chat_id)

    @dp.message(Command('login'))
    async def system_login_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer("🤖 Используйте вашего личного бота.")
            return
        await handle_login_link(message, chat_id)

    @dp.message(Command('personal_off'))
    async def system_personal_off_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        await handle_personal_off(message, chat_id)

    @dp.message(Command('today'))
    async def system_today_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer("🤖 Используйте вашего личного бота.")
            return
        await handle_today_command(message, chat_id)

    @dp.message(Command('stats'))
    async def system_stats_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer("🤖 Используйте вашего личного бота.")
            return
        await handle_stats_command(message, chat_id)

    @dp.message(Command('projects'))
    async def system_projects_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer("🤖 Используйте вашего личного бота.")
            return
        await handle_projects_command(message, chat_id)

    @dp.message(Command('project'))
    async def system_project_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Формат: /project <id>")
            return
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer("🤖 Используйте вашего личного бота.")
            return
        await handle_project_command(message, chat_id, parts[1].strip())

    @dp.message(Command('task'))
    async def system_task_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Формат: /task <id>")
            return
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer("🤖 Используйте вашего личного бота.")
            return
        await handle_task_command(message, chat_id, parts[1].strip())

    @dp.message(Command('comment'))
    async def system_comment_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("Формат: /comment <task_id> <текст>")
            return
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer("🤖 Используйте вашего личного бота.")
            return
        await handle_comment_command(message, chat_id, parts[1].strip(), parts[2].strip())

    @dp.message(Command('new_project'))
    async def system_new_project_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        raw = message.text[len('/new_project'):].strip()
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer("🤖 Используйте вашего личного бота.")
            return
        await handle_admin_new_project(message, chat_id, raw)

    @dp.message(Command('new_task'))
    async def system_new_task_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        raw = message.text[len('/new_task'):].strip()
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer("🤖 Используйте вашего личного бота.")
            return
        await handle_admin_new_task(message, chat_id, raw)

    @dp.message(Command('project_status'))
    async def system_project_status_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("Формат: /project_status <project_id> <статус>")
            return
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer("🤖 Используйте вашего личного бота.")
            return
        await handle_admin_project_status(message, chat_id, parts[1].strip(), parts[2].strip())

    @dp.message(Command('tasks'))
    async def system_tasks_handler(message: types.Message) -> None:
        chat_id = str(message.chat.id)
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer(
                "🤖 У вас настроен личный бот!\n\n"
                "Для управления задачами используйте вашего личного бота. "
                "Системный бот используется только для привязки аккаунта."
            )
            return
        await handle_tasks_command(message, chat_id)

    @dp.callback_query(F.data.startswith("complete_"))
    async def system_complete_handler(callback: types.CallbackQuery):
        chat_id = str(callback.message.chat.id)
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await callback.answer("❌ Используйте вашего личного бота для управления задачами.", show_alert=True)
            return
        await handle_complete_task(callback, chat_id)

    @dp.callback_query(F.data.startswith("task_"))
    async def system_task_open_handler(callback: types.CallbackQuery):
        chat_id = str(callback.message.chat.id)
        task_id = callback.data.split('_', 1)[1]
        await handle_task_command(callback.message, chat_id, task_id)
        await callback.answer()

    @dp.callback_query(F.data.startswith("proj_"))
    async def system_project_open_handler(callback: types.CallbackQuery):
        chat_id = str(callback.message.chat.id)
        project_id = callback.data.split('_', 1)[1]
        await handle_project_command(callback.message, chat_id, project_id)
        await callback.answer()

    @dp.callback_query(F.data.startswith("tstatus_"))
    async def system_task_status_handler(callback: types.CallbackQuery):
        chat_id = str(callback.message.chat.id)
        _, task_id, st = callback.data.split('_', 2)
        await handle_task_status_callback(callback, chat_id, task_id, st)

    @dp.callback_query(F.data.startswith("pstatus_"))
    async def system_project_status_cb_handler(callback: types.CallbackQuery):
        chat_id = str(callback.message.chat.id)
        _, project_id, st = callback.data.split('_', 2)
        await handle_project_status_callback(callback, chat_id, project_id, st)
