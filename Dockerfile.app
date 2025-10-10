FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

# [Здесь остаются ваши RUN apt-get install и pip install]
# ...

# Копируем rest of the code.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем скрипт запуска и даем ему права на исполнение
COPY run_web.sh .
RUN chmod +x run_web.sh

# Копируем остальной код.
COPY app/ .

WORKDIR /usr/src/app