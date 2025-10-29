import logging
import asyncio
import httpx
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties

from config import SYSTEM_BOT_TOKEN, DJANGO_API_BASE_URL, API_LINK_ACCOUNT, API_GET_TASKS, API_COMPLETE_TASK, API_GET_USER_BOT_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные для управления ботами
system_bot: Optional[Bot] = None
personal_bots: Dict[str, Bot] = {}  # chat_id -> Bot
dispatchers: Dict[str, Dispatcher] = {}  # chat_id -> Dispatcher
http_client = httpx.AsyncClient()

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
        logger.error(f"Error getting user bot token for {chat_id}: {e}")
    return None

async def create_personal_bot(token: str, chat_id: str):
    """Создать и запустить личного бота для пользователя"""
    try:
        bot = Bot(token=token, default=DefaultBotProperties(parse_mode='HTML'))
        dp = Dispatcher()
        
        # Регистрируем хэндлеры для личного бота
        await register_personal_bot_handlers(dp, chat_id)
        
        # Сохраняем бота и диспетчер
        personal_bots[chat_id] = bot
        dispatchers[chat_id] = dp
        
        # Запускаем polling в фоне
        asyncio.create_task(run_personal_bot_polling(dp, bot, chat_id))
        
        logger.info(f"Personal bot started for user {chat_id}")
        
    except Exception as e:
        logger.error(f"Error creating personal bot for {chat_id}: {e}")

async def register_personal_bot_handlers(dp: Dispatcher, user_chat_id: str):
    """Регистрируем хэндлеры для личного бота"""
    
    @dp.message(Command('tasks'))
    async def personal_tasks_handler(message: types.Message) -> None:
        """Обработчик /tasks для личного бота"""
        await handle_tasks_command(message, user_chat_id)
    
    @dp.callback_query(F.data.startswith("complete_"))
    async def personal_complete_handler(callback: types.CallbackQuery):
        """Обработчик выполнения задач для личного бота"""
        await handle_complete_task(callback, user_chat_id)

async def run_personal_bot_polling(dp: Dispatcher, bot: Bot, chat_id: str):
    """Запуск polling для личного бота"""
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Personal bot polling failed for {chat_id}: {e}")
        # Удаляем бота при ошибке
        if chat_id in personal_bots:
            del personal_bots[chat_id]
        if chat_id in dispatchers:
            del dispatchers[chat_id]

# --- Общие обработчики для всех ботов ---

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
            text += f"ID:{task['id']} - **{task['title']}**\n_{due_date} (в списке: {task['list_name']})_\n\n"
            builder.button(text=f"✅ Выполнить #{task['id']}", callback_data=f"complete_{task['id']}")
            
        builder.adjust(1)
        
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode='Markdown')

    except httpx.HTTPError as e:
        logger.error(f"HTTP error in tasks command: {e}")
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
                f"{callback.message.text}\n\n**-- Задача #{task_id} выполнена --**",
                parse_mode='Markdown',
                reply_markup=None
            )
        else:
            await callback.answer("❌ Не удалось завершить задачу. Возможно, она уже выполнена или не найдена.", show_alert=True)

    except httpx.HTTPError as e:
        logger.error(f"HTTP error in complete task: {e}")
        await callback.answer("❌ Ошибка соединения с сервером.", show_alert=True)

# --- Хэндлеры для системного бота ---

async def register_system_bot_handlers(dp: Dispatcher):
    """Регистрируем хэндлеры для системного бота"""
    
    @dp.message(CommandStart())
    async def system_command_start_handler(message: types.Message) -> None:
        """Обработчик /start для системного бота"""
        args = message.text.split()
        chat_id = str(message.chat.id)
        
        if len(args) > 1:
            # Привязка аккаунта
            token = args[1]
            await handle_account_linking(message, token, chat_id)
        else:
            await message.answer(
                "👋 Привет! Я бот для управления задачами.\n\n"
                "Чтобы начать, привяжите свой аккаунт, используя токен из веб-приложения.\n\n"
                "После привязки вы можете:\n"
                "• Просматривать задачи командой /tasks\n"
                "• Отмечать задачи выполненными"
            )
    
    @dp.message(Command('tasks'))
    async def system_tasks_handler(message: types.Message) -> None:
        """Обработчик /tasks для системного бота"""
        chat_id = str(message.chat.id)
        
        # Проверяем, есть ли у пользователя личный бот
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await message.answer(
                "🤖 У вас настроен личный бот!\n\n"
                "Для управления задачами используйте вашего личного бота. "
                "Системный бот используется только для привязки аккаунта."
            )
            return
        
        # Если личного бота нет, используем системного
        await handle_tasks_command(message, chat_id)
    
    @dp.callback_query(F.data.startswith("complete_"))
    async def system_complete_handler(callback: types.CallbackQuery):
        """Обработчик выполнения задач для системного бота"""
        chat_id = str(callback.message.chat.id)
        
        # Проверяем, есть ли у пользователя личный бот
        personal_token = await get_user_bot_token(chat_id)
        if personal_token:
            await callback.answer("❌ Используйте вашего личного бота для управления задачами.", show_alert=True)
            return
        
        await handle_complete_task(callback, chat_id)

async def handle_account_linking(message: types.Message, token: str, chat_id: str):
    """Обработчик привязки аккаунта"""
    try:
        response = await http_client.post(
            API_LINK_ACCOUNT, 
            json={"token": token, "chat_id": chat_id}
        )
        
        if response.status_code == 200:
            username = response.json().get('username', 'пользователь')
            
            # Проверяем, есть ли у пользователя личный бот
            personal_token = await get_user_bot_token(chat_id)
            if personal_token:
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
        logger.error(f"HTTP error in account linking: {e}")
        await message.answer("❌ Ошибка соединения с сервером.")

async def initialize_existing_personal_bots():
    """Запускаем личных ботов для уже привязанных пользователей при старте"""
    try:
        # Получаем список пользователей с привязанными личными ботами
        users_url = f"{DJANGO_API_BASE_URL}/api/v1/bot/tasks/get-users-with-personal-bots/"
        response = await http_client.get(users_url)
        
        if response.status_code == 200:
            users = response.json()
            logger.info(f"Found {len(users)} users with personal bots")
            
            for user in users:
                if user['personal_bot_token'] and user['telegram_chat_id']:
                    logger.info(f"Starting personal bot for user {user['username']}")
                    await create_personal_bot(user['personal_bot_token'], user['telegram_chat_id'])
        else:
            logger.warning(f"Failed to get users with personal bots: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error initializing personal bots: {e}")

async def main() -> None:
    """Основная функция запуска"""
    global system_bot
    
    # Инициализируем системного бота
    system_bot = Bot(token=SYSTEM_BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    system_dp = Dispatcher()
    
    # Регистрируем хэндлеры для системного бота
    await register_system_bot_handlers(system_dp)
    
    # ЗАПУСКАЕМ ЛИЧНЫХ БОТОВ ДЛЯ УЖЕ ПРИВЯЗАННЫХ ПОЛЬЗОВАТЕЛЕЙ
    logger.info("Initializing existing personal bots...")
    await initialize_existing_personal_bots()
    
    logger.info("Starting system bot...")
    await system_dp.start_polling(system_bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
    finally:
        # Закрываем HTTP клиент при завершении
        asyncio.run(http_client.aclose())