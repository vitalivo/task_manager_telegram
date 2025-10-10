from core.celery import app
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import httpx
import os
from django.db.models import Q

User = get_user_model()
DJANGO_API_BASE_URL = os.environ.get('DJANGO_API_BASE_URL', 'http://app:8000')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')


@app.task
def send_telegram_notification(user_id, message):
    """Отправка уведомления в Telegram через Bot API."""
    try:
        user = User.objects.get(id=user_id)
        chat_id = user.profile.telegram_chat_id
        
        if chat_id:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            # Используем httpx для асинхронного запроса, хотя Celery синхронный worker
            # В данном контексте это просто HTTP-запрос
            response = httpx.post(url, data=payload)
            response.raise_for_status()
            return f"Telegram notification sent to {user.username}"
        else:
            return f"User {user.username} has no linked Telegram chat ID."
    except User.DoesNotExist:
        return "User not found."
    except httpx.HTTPError as e:
        return f"Telegram API error: {e}"


@app.task
def check_deadlines():
    """Проверяет задачи, срок выполнения которых истекает, и отправляет уведомления."""
    from .models import Task
    
    now = timezone.now()
    one_hour_later = now + timedelta(hours=1)
    
    # Невыполненные задачи, срок которых наступил ИЛИ истекает в течение 1 часа
    tasks_due = Task.objects.filter(
        is_completed=False
    ).filter(
        Q(due_date__lte=now) | Q(due_date__range=(now, one_hour_later))
    ).select_related('assigned_to')

    for task in tasks_due:
        # Уведомление об истечении срока (можно добавить флаг, чтобы не спамить)
        message = f"🔴 Крайний срок! Задача '{task.title}' "
        if task.due_date <= now:
             message += "просрочена!"
        else:
             message += f"истекает через {int((task.due_date - now).total_seconds() // 60)} минут."
             
        send_telegram_notification.delay(task.assigned_to.id, message)
    
    return f"Checked {tasks_due.count()} deadlines."

# Настройка Celery Beat в settings.py
# INSTALLED_APPS = ['django_celery_beat', ...]
# CELERY_BEAT_SCHEDULE = {
#     'check-deadlines-every-5-minutes': {
#         'task': 'tasks.tasks.check_deadlines',
#         'schedule': timedelta(minutes=5),
#     },
# }