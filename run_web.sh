#!/bin/bash
# Этот скрипт выполняет полный цикл подготовки и запуска сервисов.

# --- 1. Ожидание готовности базы данных ---
echo "--- 1. Ожидание готовности PostgreSQL ---"
# Цикл ожидания, пока dbshell не сможет подключиться и выполнить простой запрос
until python manage.py dbshell -c "SELECT 1;" > /dev/null 2>&1; do
  echo "PostgreSQL недоступен, ждем 2 секунды..."
  sleep 2
done
echo "PostgreSQL готов. Продолжаем."

# --- 2. Сбор статических файлов ---
echo "--- 2. Сбор статических файлов ---"
python manage.py collectstatic --no-input

# --- 3. Применение миграций базы данных ---
echo "--- 3. Применение миграций базы данных ---"
python manage.py migrate --no-input

# --- 4. Создание суперпользователя (для доступа к админке) ---
echo "--- 4. Создание суперпользователя (admin:admin) ---"
# Используем команду runscript, чтобы создать суперпользователя только если его нет.
# ПРЕДУПРЕЖДЕНИЕ: Этот код зависит от наличия у вас скрипта, который это делает,
# или вы можете использовать следующий bash-код для создания.
# Предполагаем, что вам нужен пользователь: admin / пароль: admin
python manage.py shell << EOF
import os
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin')
if not User.objects.filter(username=username).exists():
    print(f'Создание суперпользователя: {username}')
    User.objects.create_superuser(username, email, password)
else:
    print(f'Суперпользователь {username} уже существует.')
EOF

# --- 5. Пауза для стабилизации Redis и Celery ---
echo "--- 5. Пауза 5 секунд для стабилизации сервисов ---"
sleep 5

# --- 6. Запуск Celery Worker в фоне ---
echo "--- 6. Запуск Celery Worker (в фоне) ---"
celery -A core worker -l info &

# --- 7. Запуск Celery Beat в фоне ---
echo "--- 7. Запуск Celery Beat (в фоне) ---"
celery -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler &

# --- 8. Запуск Telegram Bot в фоне ---
echo "--- 8. Запуск Telegram Bot (в фоне) ---"
# Важно: path должен быть правильным: telegram_bot/main.py
python telegram_bot/main.py &

# --- 9. Запуск Daphne (основной процесс) ---
echo "--- 9. Запуск Daphne server (основной) ---"
daphne core.asgi:application -b 0.0.0.0 -p $PORT

# Wait: Ждем завершения основного процесса Daphne.
wait
