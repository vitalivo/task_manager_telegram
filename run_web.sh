#!/bin/bash
<<<<<<< HEAD

# --- 1. ОЖИДАНИЕ ГОТОВНОСТИ POSTGRESQL (через nc) ---
echo "--- 1. Ожидание готовности PostgreSQL ---"

# Извлекаем хост и порт из DATABASE_URL
DB_HOST=$(echo $DATABASE_URL | sed -e 's/.*@\([^:]*\):.*/\1/')
DB_PORT=$(echo $DATABASE_URL | sed -e 's/.*:\([0-9]*\)\/.*/\1/')

if [ -z "$DB_PORT" ]; then
    DB_PORT=5432 # Порт по умолчанию, если не указан
fi

echo "Ожидаем $DB_HOST:$DB_PORT..."

# Ждем, пока порт не откроется (используем nc, который мы установили в Dockerfile.app)
WAIT_RETRIES=0
MAX_WAIT_RETRIES=15  # До 30 секунд ожидания (15 * 2с)

while ! nc -z "$DB_HOST" "$DB_PORT" && [ $WAIT_RETRIES -lt $MAX_WAIT_RETRIES ]; do
  echo "PostgreSQL недоступен, ждем 2 секунды... (Попытка $((WAIT_RETRIES + 1))/$MAX_WAIT_RETRIES)"
  sleep 2
  WAIT_RETRIES=$((WAIT_RETRIES + 1))
done

if [ $WAIT_RETRIES -ge $MAX_WAIT_RETRIES ]; then
    echo "--- ОШИБКА: PostgreSQL не стал доступен вовремя. Прерывание. ---"
    exit 1
fi

echo "PostgreSQL доступен! Продолжаем..."

# --- 2. МИГРАЦИИ И СТАТИЧЕСКИЕ ФАЙЛЫ ---

# Сбор статических файлов
echo "--- 2. Сбор статических файлов ---"
python manage.py collectstatic --no-input

# Применение миграций базы данных
echo "--- 3. Применение миграций базы данных ---"
python manage.py migrate --no-input

# Создание суперпользователя (если он еще не существует)
echo "--- 4. Создание суперпользователя admin:admin ---"
# Используем команду, которая создает суперпользователя только если он не существует
python manage.py createsuperuser --noinput --username admin --email admin@example.com || true

# --- 5. ЗАПУСК ВСЕХ ФОНОВЫХ ПРОЦЕССОВ В ФОНЕ (для Free Tier) ---

echo "--- 5. Запуск фоновых процессов: Celery Worker, Celery Beat и Telegram Bot ---"

# 5.1. Celery Worker (Обработчик задач)
echo "Запуск Celery Worker..."
celery -A core worker -l info &

# 5.2. Celery Beat (Планировщик)
echo "Запуск Celery Beat..."
celery -A core beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler &

# 5.3. Telegram Bot
echo "Запуск Telegram Bot..."
python telegram_bot/main.py &

# --- 6. ЗАПУСК ГЛАВНОГО ПРОЦЕССА (DAPHNE) ---

# Запускаем Daphne как основной процесс, чтобы контейнер не завершался.
echo "--- 6. Запуск Daphne (ASGI-сервера) на порту $PORT ---"
# exec гарантирует, что Daphne заменит этот bash скрипт, что является лучшей практикой.
exec daphne core.asgi:application -b 0.0.0.0 -p $PORT
=======
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
>>>>>>> 62f429b61b500409a8079f3edf79c34361ca81e4
