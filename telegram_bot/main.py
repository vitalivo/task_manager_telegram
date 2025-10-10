import logging
import asyncio
import httpx

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, API_LINK_ACCOUNT, API_GET_TASKS, API_COMPLETE_TASK

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
http_client = httpx.AsyncClient()


# --- Хэндлер: /start и Привязка аккаунта ---

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> None:
    args = message.text.split()
    
    if len(args) > 1:
        token = args[1]
        chat_id = message.chat.id
        
        try:
            response = await http_client.post(API_LINK_ACCOUNT, json={"token": token, "chat_id": str(chat_id)})
            
            if response.status_code == 200:
                username = response.json().get('username', 'пользователь')
                await message.answer(f"✅ Аккаунт успешно привязан! Добро пожаловать, {username}. Теперь вы можете управлять задачами с помощью /tasks.")
            else:
                await message.answer("❌ Ошибка привязки. Неверный токен или токен уже использован.")
        except httpx.HTTPError:
             await message.answer("❌ Ошибка соединения с сервером Django.")
        
    else:
        await message.answer("👋 Привет! Я бот для управления задачами. Чтобы начать, привяжите свой аккаунт, используя токен из веб-приложения.")


# --- Хэндлер: /tasks (Просмотр задач) ---

@dp.message(Command('tasks'))
async def command_tasks_handler(message: types.Message) -> None:
    chat_id = message.chat.id
    
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
            
        builder.adjust(1) # Кнопки в столбик
        
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode='Markdown')

    except httpx.HTTPError:
        await message.answer("❌ Ошибка соединения с сервером Django.")


# --- Хэндлер: Callback (Выполнение задачи) ---

@dp.callback_query(F.data.startswith("complete_"))
async def callback_complete_task(callback: types.CallbackQuery):
    task_id = callback.data.split("_")[1]
    chat_id = callback.message.chat.id
    
    try:
        response = await http_client.post(API_COMPLETE_TASK, json={"chat_id": str(chat_id), "task_id": task_id})
        
        if response.status_code == 200:
            await callback.answer(f"✅ Задача #{task_id} отмечена как выполненная!", show_alert=True)
            # Обновляем сообщение, чтобы удалить кнопку
            await callback.message.edit_text(
                f"{callback.message.text}\n\n**-- Задача #{task_id} выполнена --**",
                parse_mode='Markdown',
                reply_markup=None
            )
        else:
            await callback.answer("❌ Не удалось завершить задачу. Возможно, она уже выполнена или не найдена.", show_alert=True)

    except httpx.HTTPError:
        await callback.answer("❌ Ошибка соединения с сервером Django.", show_alert=True)


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")