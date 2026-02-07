# TaskFlow

Профессиональная система управления задачами с Telegram‑интеграцией, WebSocket‑обновлениями и фоновыми процессами.

**Что это**
TaskFlow — это единая платформа для задач и проектов с веб‑интерфейсом, API и Telegram‑ботом. Подходит для небольшой команды сегодня и масштабируется на production завтра.

**Ключевые возможности**
- Реальное время: обновления задач через WebSockets.
- Telegram‑бот: просмотр, изменение задач и проектов.
- Умные напоминания: дедлайны через Celery.
- Командная работа: роли, доступы, аудит действий.
- Безопасность: разделение прав, валидации, токены входа.

**Технологии**
- Backend: Django, DRF, Channels, Celery.
- Infra: Redis, PostgreSQL, Docker.
- UI: HTML/CSS/JS, WebSockets.

---

## Быстрый старт (Docker)

```bash
# Запуск всех сервисов
docker compose up -d --build

# Миграции и суперпользователь
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser
```

Откройте:
- Веб: `http://localhost:8005`
- Админка: `http://localhost:8005/admin`
- Swagger: `http://localhost:8005/api/docs/`
- Healthcheck: `http://localhost:8005/health/`

---

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните ключи.

Минимально необходимые:
- `SECRET_KEY`
- `DEBUG`
- `DATABASE_URL`
- `REDIS_URL`
- `SYSTEM_BOT_TOKEN`
- `TELEGRAM_BOT_TOKEN`

Важно:
- Для Docker‑compose оставьте `DJANGO_API_BASE_URL=http://app:8000`.
- Для запуска бота вне Docker используйте `DJANGO_API_BASE_URL=http://localhost:8005`.

---

## Архитектура

Компоненты:
- `app`: Django + DRF + Channels (ASGI, daphne)
- `telegram_bot`: aiogram‑бот (системный + личные боты)
- `celery_worker`: фоновые задачи
- `celery_beat`: расписание задач
- `db`: PostgreSQL
- `redis`: каналы + кэш + брокер очередей

WebSocket endpoint:
- `ws://<host>/ws/tasks/` (или `wss://` в продакшене)

---

## Telegram‑бот

Базовые команды:
- `/start` — привязка аккаунта
- `/tasks` — список задач
- `/help` — справка

Полный список:
- `/today` — задачи на сегодня
- `/stats` — статистика задач
- `/projects` — мои проекты
- `/project <id>` — карточка проекта
- `/task <id>` — карточка задачи
- `/comment <task_id> <текст>` — комментарий к задаче
- `/login` — одноразовая ссылка входа в веб
- `/personal_off` — отключить личного бота

Админ/менеджер:
- `/new_project <Название | Клиент | Описание>`
- `/new_task <project_id | Заголовок | username(опц.) | описание(опц.)>`
- `/project_status <project_id> <статус>`

Личный бот:
- Настраивается в веб‑интерфейсе.
- Команды такие же, но бот работает только с вашими задачами.

---

## API (примеры)

Список задач:
`/api/v1/tasks/?status=in_progress&list=1&assigned_to=2&q=тест&ordering=-due_date`

Статистика:
`/api/v1/tasks/stats/`

Аудит:
`/api/v1/tasks/<id>/audit/`

Bot API:
`/api/bot/*` (например `/api/bot/get_user_tasks/`, `/api/bot/today/`, `/api/bot/link-account/`)

---

## Тесты

```bash
docker compose run --rm --build app python manage.py test
```

---

## Масштабирование

- Увеличивайте количество `web` и `celery_worker` инстансов.
- Выносите PostgreSQL и Redis в управляемые сервисы.
- Переводите Telegram‑бота на webhook для стабильности и экономии ресурсов.
- Используйте отдельный CDN или S3 для медиа.

---

## Деплой и домен

Подходит Render или любой Docker‑хостинг:
- Web: Django + daphne
- Worker: Celery worker
- Beat: Celery beat
- Bot: отдельный воркер или webhook

При подключении домена:
- Настройте DNS и HTTPS у провайдера.
- Укажите `WEB_BASE_URL` и `DJANGO_API_BASE_URL`.
- Проверьте WebSocket и Telegram‑бота.

---

## Локальная проверка (чек‑лист)

1. `docker compose up -d --build`
2. `docker compose exec app python manage.py migrate`
3. `docker compose exec app python manage.py createsuperuser`
4. Откройте `http://localhost:8005` и войдите.
5. Привяжите Telegram через `/start <токен>`.
6. Проверьте команды бота: `/tasks`, `/today`, `/stats`, `/projects`.
7. При необходимости включите личного бота в веб‑интерфейсе.
