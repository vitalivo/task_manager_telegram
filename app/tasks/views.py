# app/tasks/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny # <-- НОВЫЙ ИМПОРТ
from django.db import models # <-- НОВЫЙ ИМПОРТ (для models.Q)
import uuid # <-- НОВЫЙ ИМПОРТ

from .models import Task, TeamList
from .serializers import TaskSerializer
from users.models import UserProfile
from django.shortcuts import get_object_or_404
# from .signals import task_post_save_handler # Эта функция вызывается сигналом, не нужно импортировать сюда

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

# =======================================================
# ЗАГЛУШКА УВЕДОМЛЕНИЙ (ПОКА НЕ БУДЕТ ИСПРАВЛЕН SIGNALS.PY)
# В чистой архитектуре эти вызовы нужно убрать, 
# полагаясь только на task.save(), который вызывает сигнал.
def notify_task_update(task):
    """Заглушка для вызова уведомлений до полной настройки сигналов."""
    from .signals import notify_channels, notify_telegram
    notify_channels(task, 'updated')
    if not task.is_completed:
        message = f"🔄 Задача изменена: '{task.title}'."
        notify_telegram(task, message)
# =======================================================


class TaskFrontendView(LoginRequiredMixin, TemplateView):
    """View для отображения основной страницы задач с Websocket и Vanilla JS."""
    template_name = 'tasks/index.html'

    # get_context_data здесь не нужен, как и указано.


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        # Пользователь видит только задачи, назначенные ему или созданные им
        user = self.request.user
        return Task.objects.filter(models.Q(assigned_to=user) | models.Q(created_by=user)).select_related('list', 'assigned_to')

    # Примечание: Вызов notify_task_update здесь (в perform_create/update) 
    # является избыточным, так как task.save() вызовет сигнал. 
    # В чистой архитектуре его стоит удалить, но для гарантированной работы 
    # оставляем, пока не убедимся в работе сигналов.

    def perform_create(self, serializer):
        task = serializer.save(created_by=self.request.user)
        # task.save() вызовет сигнал task_post_save_handler
        # notify_task_update(task) # Закомментировано для чистоты

    def perform_update(self, serializer):
        task = serializer.save()
        # task.save() вызовет сигнал task_post_save_handler
        # notify_task_update(task) # Закомментировано для чистоты


    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = get_object_or_404(Task, pk=pk)
        if task.assigned_to != request.user and task.created_by != request.user:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)
        
        task.is_completed = True
        # task.save() вызывает сигнал task_post_save_handler для уведомлений
        task.save(update_fields=['is_completed']) 
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)


class TaskBotAPIView(viewsets.ViewSet):
    # ЯВНО ОТКЛЮЧАЕМ АУТЕНТИФИКАЦИЮ И ПРАВА ДЛЯ ВСЕГО BOT VIEWSET.
    # Это решает проблему 403 Forbidden для link-account.
    permission_classes = [AllowAny]
    authentication_classes = [] 
    
    # ПРИМЕЧАНИЕ ПО БЕЗОПАСНОСТИ: В боевой системе get_user_tasks и 
    # complete_task_bot должны быть защищены с помощью Custom API Key Authentication.
    @action(detail=False, methods=['get'], url_path='get_user_tasks')
    def get_user_tasks(self, request):
        chat_id = request.query_params.get('chat_id')
        print(f"DEBUG: Received chat_id for /tasks: {chat_id}, Type: {type(chat_id)}")
        try:
            profile = UserProfile.objects.get(telegram_chat_id=chat_id)
            tasks = Task.objects.filter(assigned_to=profile.user, is_completed=False)
            serializer = TaskSerializer(tasks, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='complete-task')
    def complete_task_bot(self, request):
        chat_id = request.data.get('chat_id')
        task_id = request.data.get('task_id')

        try:
            profile = UserProfile.objects.get(telegram_chat_id=chat_id)
            task = Task.objects.get(id=task_id, assigned_to=profile.user, is_completed=False)
            task.is_completed = True
            task.save(update_fields=['is_completed'])
            return Response({"status": "completed"}, status=status.HTTP_200_OK)
        except (UserProfile.DoesNotExist, Task.DoesNotExist):
            return Response({"error": "Task or User not found/linked"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='link-account')
    def link_account(self, request):
        token = request.data.get('token')
        chat_id = request.data.get('chat_id')

        if not token or not chat_id:
            return Response({"error": "Missing token or chat_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            profile = UserProfile.objects.get(verification_token=token)
            
            # Сохраняем chat_id, сбрасываем токен и привязываем
            profile.telegram_chat_id = str(chat_id) # Обеспечиваем сохранение как строка
            profile.verification_token = uuid.uuid4() 
            profile.save(update_fields=['telegram_chat_id', 'verification_token'])
            return Response({"status": "Account linked", "username": profile.user.username}, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)