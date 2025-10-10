FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

# --- [КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Установка системных зависимостей] ---
# libpq-dev: Необходим для psycopg2-binary
# build-essential: Набор инструментов для компиляции (нужен для многих библиотек, таких как cryptography)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Копируем файл зависимостей
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем остальной код. Поскольку вы используете COPY app/ ., 
# я предполагаю, что manage.py находится в /usr/src/app/manage.py
COPY app/ . 