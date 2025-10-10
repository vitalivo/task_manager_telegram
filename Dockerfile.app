FROM python:3.11-slim

# Убеждаемся, что Python и Daphne не буферизуют вывод
ENV PYTHONUNBUFFERED 1
# Render использует переменную PORT для определения, на каком порту запускать Web Service
ENV PORT 10000

# --- УСТАНОВКА СИСТЕМНЫХ ЗАВИСИМОСТЕЙ ---
# netcat нужен для скрипта ожидания базы данных (wait-for-db)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    netcat-traditional \
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

# Копируем основной код Django приложения
COPY app/ .

# !!! ДОБАВЛЕНИЕ КОДА БОТА !!!
# Копируем код Telegram-бота, чтобы он был доступен внутри контейнера,
# рядом с Django-кодом, по пути 'telegram_bot/'.
COPY telegram_bot/ telegram_bot/

# Команда запуска (она указана в настройках Render)
# CMD ["./run_web.sh"]