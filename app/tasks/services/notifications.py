from __future__ import annotations

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import httpx

from ..serializers import TaskSerializer
from ..tasks import send_telegram_notification
from ..models import ProjectMember


def notify_channels(task) -> None:
    """Отправляет уведомление через Channels (Websocket)."""
    try:
        channel_layer = get_channel_layer()
        task_data = TaskSerializer(task).data

        recipient_ids = set()
        if task.assigned_to_id:
            recipient_ids.add(task.assigned_to_id)
        if task.created_by_id:
            recipient_ids.add(task.created_by_id)

        member_ids = ProjectMember.objects.filter(
            project=task.list,
            is_active=True,
        ).values_list('user_id', flat=True)
        recipient_ids.update(member_ids)

        for user_id in recipient_ids:
            group_name = f"user_{user_id}"
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "task_update",
                    "message": task_data,
                }
            )
    except Exception:
        # Don't crash main flow on websocket errors
        pass


def _send_personal_telegram_notification_sync(bot_token: str, chat_id: str, message: str) -> bool:
    """Синхронная отправка уведомления через личного бота."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        response = httpx.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
            },
            timeout=5,
        )
        response.raise_for_status()
        return True
    except Exception:
        return False


def notify_telegram(task, message: str) -> None:
    """Отправляет уведомление через личного бота или системного (Celery)."""
    try:
        if task.assigned_to and not task.is_completed:
            profile = task.assigned_to.profile
            if profile.personal_bot_token and profile.telegram_chat_id:
                _send_personal_telegram_notification_sync(
                    profile.personal_bot_token,
                    profile.telegram_chat_id,
                    message,
                )
            else:
                send_telegram_notification.delay(task.assigned_to.id, message)
    except Exception:
        pass
