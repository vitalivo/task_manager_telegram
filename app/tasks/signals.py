from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .serializers import TaskSerializer
from .tasks import send_telegram_notification
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task

def notify_channels(task, action_type):
    """Отправляет уведомление через Channels (Websocket)."""
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

def notify_telegram(task, message):
    """Отправляет уведомление через Celery/Telegram."""
    if task.assigned_to and not task.is_completed:
        send_telegram_notification.delay(task.assigned_to.id, message)
        print(f"Celery Telegram notification queued for {task.assigned_to.username}")

@receiver(post_save, sender=Task)
def task_post_save_handler(sender, instance, created, **kwargs):
    """Обработчик, вызываемый после сохранения задачи."""
    
    # WS-уведомление (всегда)
    notify_channels(instance, 'updated')
    
    # Telegram-уведомление (только при создании/назначении)
    if created:
        message = f"🚨 **Новая задача** назначена вам: '{instance.title}'! Срок: {instance.due_date.strftime('%d.%m %H:%M') if instance.due_date else 'Не установлен'}"
        notify_telegram(instance, message)
    elif 'is_completed' in kwargs.get('update_fields', set()):
        # Если задача завершена, не отправляем уведомление о назначении
        pass
    else:
        # Уведомление об изменении (если не завершена)
        message = f"🔄 **Задача изменена**: '{instance.title}'. Срок: {instance.due_date.strftime('%d.%m %H:%M') if instance.due_date else 'Не установлен'}"
        notify_telegram(instance, message)