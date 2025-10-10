FROM python:3.11-slim

# Убеждаемся, что Python и Daphne не буферизуют вывод
ENV PYTHONUNBUFFERED 1
# Render использует переменную PORT для определения, на каком порту запускать Web Service
ENV PORT 10000

# --- УСТАНОВКА СИСТЕМНЫХ ЗАВИСИМОСТЕЙ ---
# libpq-dev необходим для psycopg2-binary
# build-essential необходим для компиляции некоторых Python-пакетов (например, cryptography)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# --- УСТАНОВКА РАБОЧЕЙ ДИРЕКТОРИИ ---
# Все последующие команды (COPY, RUN) будут выполняться внутри этой папки
WORKDIR /usr/src/app

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем скрипт запуска и даем ему права на исполнение
COPY run_web.sh .
RUN chmod +x run_web.sh

# Копируем основной код приложения
# Предполагается, что 'manage.py' находится в корне проекта и его содержимое скопируется
COPY app/ .

# Команда запуска (она указана в настройках Render, но здесь для справки)
# CMD ["./run_web.sh"]