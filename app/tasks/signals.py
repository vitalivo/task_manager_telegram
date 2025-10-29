# tasks/signals.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .serializers import TaskSerializer
from .tasks import send_telegram_notification
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task
import httpx

def send_personal_telegram_notification_sync(bot_token, chat_id, message):
    """Синхронная отправка уведомления через личного бота"""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = httpx.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        })
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending personal Telegram notification: {e}")
        return False

def notify_channels(task, action_type):
    """Отправляет уведомление через Channels (Websocket)."""
    try:
        channel_layer = get_channel_layer()
        task_data = TaskSerializer(task).data
        
        if task.assigned_to:
            group_name = f"user_{task.assigned_to.id}"
            
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "task_update",
                    "message": task_data
                }
            )
            print(f"WS notification sent to {task.assigned_to.username} for task {task.id}")
    except Exception as e:
        print(f"Error in notify_channels: {e}")

def notify_telegram(task, message):
    """Отправляет уведомление через Celery/Telegram."""
    try:
        if task.assigned_to and not task.is_completed:
            # Проверяем есть ли личный бот
            profile = task.assigned_to.profile
            if profile.personal_bot_token and profile.telegram_chat_id:
                # Используем личного бота (синхронная версия)
                success = send_personal_telegram_notification_sync(
                    profile.personal_bot_token,
                    profile.telegram_chat_id,
                    message
                )
                if success:
                    print(f"Personal Telegram notification sent to {task.assigned_to.username}")
                else:
                    print(f"Failed to send personal Telegram notification to {task.assigned_to.username}")
            else:
                # Используем системного бота (старая логика через Celery)
                send_telegram_notification.delay(task.assigned_to.id, message)
                print(f"System Telegram notification queued for {task.assigned_to.username}")
    except Exception as e:
        print(f"Error in notify_telegram: {e}")

@receiver(post_save, sender=Task)
def task_post_save_handler(sender, instance, created, **kwargs):
    """Обработчик, вызываемый после сохранения задачи."""
    
    try:
        # WS-уведомление (всегда)
        notify_channels(instance, 'updated')
        
        # Проверяем что update_fields не None
        update_fields = kwargs.get('update_fields') or set()
        
        # Telegram-уведомление (только при создании/назначении)
        if created:
            message = f"🚨 **Новая задача** назначена вам: '{instance.title}'! Срок: {instance.due_date.strftime('%d.%m %H:%M') if instance.due_date else 'Не установлен'}"
            notify_telegram(instance, message)
        elif 'is_completed' in update_fields:
            # Если задача завершена, не отправляем уведомление
            pass
        else:
            message = f"🔄 **Задача изменена**: '{instance.title}'. Срок: {instance.due_date.strftime('%d.%m %H:%M') if instance.due_date else 'Не установлен'}"
            notify_telegram(instance, message)
            
    except Exception as e:
        print(f"Error in task_post_save_handler: {e}")