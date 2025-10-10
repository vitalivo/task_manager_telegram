# app/core/asgi.py (ИСПРАВЛЕННЫЙ КОД)

import os
from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack # <--- (1) НОВЫЙ ИМПОРТ
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django_asgi_app = get_asgi_application()

from tasks import consumers

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        # Оберните AuthMiddlewareStack в SessionMiddlewareStack
        SessionMiddlewareStack( # <--- (2) ДОБАВЛЕНИЕ SessionMiddlewareStack
            AuthMiddlewareStack(
                URLRouter([
                    path('ws/tasks/', consumers.TaskConsumer.as_asgi()),
                ])
            )
        )
    ),
})
