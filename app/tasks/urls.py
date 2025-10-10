# app/tasks/urls.py
from django.urls import path
from .views import TaskFrontendView

urlpatterns = [
    # Основная страница веб-приложения для отображения задач
    path('', TaskFrontendView.as_view(), name='task_dashboard'),
]