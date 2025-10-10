#!/bin/bash

# Мы используем External Connection String (полный URL) для DATABASE_URL,
# чтобы обойти проблемы с Internal DNS в Docker-образе Render.

echo "--- 1. Ожидание готовности PostgreSQL ---"

# --- ОБНОВЛЕННАЯ ЛОГИКА ИЗВЛЕЧЕНИЯ ХОСТА И ПОРТА (Используем только стандартный sed) ---

DB_URI=$DATABASE_URL

# Извлекаем хост: берем всё после '@', затем удаляем всё после первого ':' и '/'.
# Это наиболее надежный способ получить только имя хоста.
DB_HOST=$(echo $DB_URI | sed 's|.*@||; s|/.*||; s|:.*||')

# Извлекаем порт: берем всё после последней ':' в части host:port/db, затем удаляем всё после '/'.
DB_PORT=$(echo $DB_URI | sed 's|.*:||; s|/.*||')

# Если порт не является числом (т.е. был пропущен в URL, как это часто бывает),
# или команда sed не смогла его корректно извлечь, используем порт по умолчанию.
if ! [[ "$DB_PORT" =~ ^[0-9]+$ ]]; then
    DB_PORT="5432"
fi

# -------------------------------------------------------------------

if [ -z "$DB_HOST" ]; then
    echo "Ошибка: Не удалось извлечь хост из DATABASE_URL."
    echo "Убедитесь, что переменная установлена в формате postgresql://user:pass@host:port/db_name"
    exit 1
fi

MAX_ATTEMPTS=15
for i in $(seq 1 $MAX_ATTEMPTS); do
    echo "Ожидаем $DB_HOST:$DB_PORT..."
    # Проверка доступности PostgreSQL (используем nc)
    if nc -z -w 1 $DB_HOST $DB_PORT 2>/dev/null; then
        echo "PostgreSQL доступен!"
        break
    else
        echo "PostgreSQL недоступен, ждем 2 секунды... (Попытка $i/$MAX_ATTEMPTS)"
        sleep 2
    fi

    if [ $i -eq $MAX_ATTEMPTS ]; then
        echo "Превышено максимальное время ожидания PostgreSQL. Выход."
        exit 1
    fi
done

echo "--- 2. Выполнение миграций и сбор статики ---"
# Используем python3 вместо python для явного указания интерпретатора.
python3 manage.py collectstatic --noinput
python3 manage.py migrate

echo "--- 3. Запуск Daphne (Web Service) ---"
# Запускаем основной веб-процесс (ASGI), явно указывая путь к daphne, если это необходимо.
# На Render это обычно не требуется, но python3 - это хорошая практика.
/usr/local/bin/daphne core.asgi:application --port $PORT --bind 0.0.0.0
