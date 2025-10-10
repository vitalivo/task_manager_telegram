#!/bin/bash
# Этот скрипт запускает все необходимые компоненты (Web, Worker, Beat, Bot)
# внутри одного процесса, чтобы соответствовать ограничениям Render Free Tier.

echo "--- 1. Сбор статических файлов ---"
python manage.py collectstatic --no-input

echo "--- 2. Применение миграций базы данных ---"
python manage.py migrate --no-input

# --- 3. Запуск Celery Worker в фоне ---
# Worker обрабатывает асинхронные задачи.
echo "--- 3. Запуск Celery Worker (в фоне) ---"
celery -A core worker -l info &

# --- 4. Запуск Celery Beat в фоне ---
# Beat запускает запланированные задачи (например, проверку просроченных задач).
echo "--- 4. Запуск Celery Beat (в фоне) ---"
celery -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler &

# --- 5. Запуск Telegram Bot в фоне ---
# Запуск основного скрипта бота.
echo "--- 5. Запуск Telegram Bot (в фоне) ---"
python telegram_bot/main.py &

# --- 6. Запуск Daphne (основной процесс) ---
# Daphne должен быть основным процессом, чтобы Web Service оставался активным.
echo "--- 6. Запуск Daphne server (основной) ---"
daphne core.asgi:application -b 0.0.0.0 -p $PORT

# Wait: Ждем завершения основного процесса Daphne.
wait