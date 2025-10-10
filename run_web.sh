#!/bin/bash

# 1. Сбор статических файлов
echo "Starting collectstatic..."
python manage.py collectstatic --no-input

# 2. Применение миграций базы данных
echo "Starting database migrations..."
python manage.py migrate --no-input

# 3. Запуск Daphne (ASGI-сервера)
echo "Starting Daphne server..."
daphne core.asgi:application -b 0.0.0.0 -p $PORT