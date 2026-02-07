FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN echo '#!/bin/bash\n\
python manage.py migrate\n\
python manage.py collectstatic --no-input\n\
daphne core.asgi:application -b 0.0.0.0 -p 8000' > /usr/src/app/run.sh \
&& chmod +x /usr/src/app/run.sh