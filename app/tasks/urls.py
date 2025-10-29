# app/tasks/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskFrontendView, TaskViewSet, TaskBotAPIView

router = DefaultRouter()
router.register(r'api/tasks', TaskViewSet, basename='task')
router.register(r'api/bot', TaskBotAPIView, basename='bot')

urlpatterns = [
    path('', TaskFrontendView.as_view(), name='task_dashboard'),
    path('', include(router.urls)),
]