# tasks/signals.py
import logging

from .services.notifications import notify_channels, notify_telegram
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Task)
def task_post_save_handler(sender, instance, created, **kwargs):
    """Обработчик, вызываемый после сохранения задачи."""

    try:
        # WS-уведомление (всегда)
        notify_channels(instance)
        
        # Проверяем что update_fields не None
        update_fields = set(kwargs.get('update_fields') or [])
        
        # Telegram-уведомление (только при создании/назначении)
        if created:
            message = f"🚨 Новая задача назначена вам: '{instance.title}'! Срок: {instance.due_date.strftime('%d.%m %H:%M') if instance.due_date else 'Не установлен'}"
            notify_telegram(instance, message)
        elif instance.is_completed and update_fields.issubset({'is_completed', 'status', 'completed_at'}):
            # Если задача завершена (или синхронизация статуса/даты завершения), не отправляем уведомление
            pass
        else:
            message = f"🔄 Задача изменена: '{instance.title}'. Срок: {instance.due_date.strftime('%d.%m %H:%M') if instance.due_date else 'Не установлен'}"
            notify_telegram(instance, message)
            
    except Exception as e:
        logger.exception("Error in task_post_save_handler: %s", e)
