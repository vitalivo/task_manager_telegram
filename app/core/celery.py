import os
from celery import Celery
from django.conf import settings

# Устанавливаем настройки Django для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Используем настройки Django для Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически находим таски в приложениях
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)