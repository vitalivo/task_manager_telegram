import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

class TaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.user = self.scope["user"]
            self.user_group_name = f'user_{self.user.id}'
            await self.channel_layer.group_add(
                self.user_group_name,
                self.channel_name
            )
            await self.accept()
            logger.info("WS connected for user: %s", self.user.username)
        else:
            await self.close()
            logger.warning("WS connection rejected (unauthenticated)")

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            logger.info("WS disconnected for user: %s", self.user.username)
    async def task_update(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'task_update',
            'task': message
        }))
