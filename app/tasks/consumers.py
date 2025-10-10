import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()

class TaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Аутентификация пользователя (предполагаем, что сессия уже установлена через DRF/Django)
        # Для простоты: используем self.scope["user"] из аутентификации Django Channels
        if self.scope["user"].is_authenticated:
            self.user = self.scope["user"]
            self.user_group_name = f'user_{self.user.id}'

            # Добавляем канал в группу пользователя
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            await self.accept()
            print(f"WS connected for user: {self.user.username}")
        else:
            await self.close()
            print("WS connection rejected (unauthenticated)")

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            print(f"WS disconnected for user: {self.user.username}")
            
    # Получение сообщений от группы (например, при обновлении задачи)
    async def task_update(self, event):
        message = event['message']
        
        # Отправка сообщения клиенту
        await self.send(text_data=json.dumps({
            'type': 'task_update',
            'data': message
        }))