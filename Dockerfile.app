FROM python:3.11-slim

# Убеждаемся, что Python и Daphne не буферизуют вывод
ENV PYTHONUNBUFFERED 1

# --- УСТАНОВКА СИСТЕМНЫХ ЗАВИСИМОСТЕЙ ---
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /usr/src/app

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем скрипт запуска если его нет
RUN echo '#!/bin/bash\n\
python manage.py migrate\n\
python manage.py collectstatic --no-input\n\
daphne core.asgi:application -b 0.0.0.0 -p 8000' > /usr/src/app/run.sh \
&& chmod +x /usr/src/app/run.sh