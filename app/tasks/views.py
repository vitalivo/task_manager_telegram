# app/tasks/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.db import models
import uuid
from django.db.models import Q
from .models import Task, TeamList
from .serializers import TaskSerializer
from users.models import UserProfile
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

# =======================================================
# ЗАГЛУШКА УВЕДОМЛЕНИЙ (ПОКА НЕ БУДЕТ ИСПРАВЛЕН SIGNALS.PY)
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


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        user = self.request.user
        return Task.objects.filter(models.Q(assigned_to=user) | models.Q(created_by=user)).select_related('list', 'assigned_to')

    def perform_create(self, serializer):
        task = serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        task = serializer.save()

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = get_object_or_404(Task, pk=pk)
        if task.assigned_to != request.user and task.created_by != request.user:
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)
        
        task.is_completed = True
        task.save(update_fields=['is_completed']) 
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get', 'post', 'delete'], url_path='personal-bot')
    def personal_bot(self, request):
        """Управление личным ботом пользователя"""
        user_profile = request.user.profile
        
        if request.method == 'GET':
            return Response({
                'personal_bot_token': user_profile.personal_bot_token,
                'personal_bot_username': user_profile.personal_bot_username,
                'is_bot_active': bool(user_profile.personal_bot_token),
                'telegram_linked': bool(user_profile.telegram_chat_id)
            })
        
        elif request.method == 'POST':
            token = request.data.get('token')
            username = request.data.get('username')
            
            if not token:
                return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            user_profile.personal_bot_token = token
            user_profile.personal_bot_username = username
            
            # АВТОМАТИЧЕСКАЯ ПРИВЯЗКА: Если пользователь уже привязал Telegram к системному боту,
            # используем тот же chat_id для личного бота
            if not user_profile.telegram_chat_id:
                try:
                    # Проверяем, есть ли у этого пользователя привязанный chat_id в ЛЮБОМ из его профилей
                    existing_with_chat = UserProfile.objects.filter(
                        user=request.user, 
                        telegram_chat_id__isnull=False
                    ).exclude(id=user_profile.id).first()
                    
                    if existing_with_chat and existing_with_chat.telegram_chat_id:
                        user_profile.telegram_chat_id = existing_with_chat.telegram_chat_id
                        print(f"Auto-linked chat_id {user_profile.telegram_chat_id} to personal bot")
                except Exception as e:
                    print(f"Error auto-linking chat_id: {e}")
            
            user_profile.save()
            
            return Response({
                "status": "Bot token updated",
                "username": username,
                "chat_id_linked": bool(user_profile.telegram_chat_id)
            })
        
        elif request.method == 'DELETE':
            user_profile.personal_bot_token = None
            user_profile.personal_bot_username = None
            user_profile.save()
            return Response({"status": "Bot settings cleared"})


class TaskBotAPIView(viewsets.ViewSet):
    permission_classes = [AllowAny]
    authentication_classes = [] 
    
    @action(detail=False, methods=['get'], url_path='get_user_tasks')
    def get_user_tasks(self, request):
        chat_id = request.query_params.get('chat_id')
        print(f"DEBUG: Received chat_id for /tasks: {chat_id}, Type: {type(chat_id)}")
        try:
            profile = UserProfile.objects.get(telegram_chat_id=chat_id)
        
            tasks = Task.objects.filter(
                models.Q(assigned_to=profile.user) | models.Q(created_by=profile.user),
                is_completed=False
            ).select_related('list', 'assigned_to')
        
            serializer = TaskSerializer(tasks, many=True)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='link-account')
    def link_account(self, request):
        token = request.data.get('token')
        chat_id = request.data.get('chat_id')

        if not token or not chat_id:
            return Response({"error": "Missing token or chat_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            profile = UserProfile.objects.get(verification_token=token)
            
            profile.telegram_chat_id = str(chat_id)
            profile.verification_token = uuid.uuid4() 
            profile.save(update_fields=['telegram_chat_id', 'verification_token'])
            return Response({"status": "Account linked", "username": profile.user.username}, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=False, methods=['post'], url_path='link-existing-user')
    def link_existing_user(self, request):
        """Привязать chat_id к существующему пользователю по username"""
        username = request.data.get('username')
        chat_id = request.data.get('chat_id')

        if not username or not chat_id:
            return Response({"error": "Missing username or chat_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            User = get_user_model()
            user = User.objects.get(username=username)
            profile = user.profile
            
            profile.telegram_chat_id = str(chat_id)
            profile.save()
            
            return Response({
                "status": "User linked", 
                "username": user.username,
                "personal_bot": profile.personal_bot_username
            })
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'], url_path='link-by-email')
    def link_by_email(self, request):
        """Привязать chat_id по email"""
        email = request.data.get('email')
        chat_id = request.data.get('chat_id')

        if not email or not chat_id:
            return Response({"error": "Missing email or chat_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            User = get_user_model()
            user = User.objects.get(email=email)
            profile = user.profile
            
            profile.telegram_chat_id = str(chat_id)
            profile.save()
            
            return Response({
                "status": "User linked by email", 
                "username": user.username,
                "email": user.email
            })
        except User.DoesNotExist:
            return Response({"error": "User with this email not found"}, status=status.HTTP_404_NOT_FOUND)
        
    @action(detail=False, methods=['get'], url_path='get-user-bot-token')
    def get_user_bot_token(self, request):
        """Получить токен личного бота пользователя"""
        chat_id = request.query_params.get('chat_id')
    
        try:
            profile = UserProfile.objects.get(telegram_chat_id=chat_id)
            return Response({
                'personal_bot_token': profile.personal_bot_token,
                'personal_bot_username': profile.personal_bot_username
            })
        except UserProfile.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'], url_path='get-users-with-personal-bots')
    def get_users_with_personal_bots(self, request):
        """Получить пользователей с настроенными личными ботами"""
        try:
            profiles = UserProfile.objects.filter(
                personal_bot_token__isnull=False,
                telegram_chat_id__isnull=False
            ).select_related('user')
            
            users_data = []
            for profile in profiles:
                users_data.append({
                    'username': profile.user.username,
                    'telegram_chat_id': profile.telegram_chat_id,
                    'personal_bot_token': profile.personal_bot_token,
                    'personal_bot_username': profile.personal_bot_username
                })
            
            return Response(users_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)