# app/tasks/apps.py

from django.apps import AppConfig

class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tasks'

    def ready(self):
        # Импортируем сигналы при запуске приложения
        import tasks.signals
