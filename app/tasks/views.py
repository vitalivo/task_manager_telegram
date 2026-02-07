# app/tasks/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.exceptions import PermissionDenied
from django.db import models
import uuid
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, time

from .models import Client, ProjectMember, Task, TaskComment, TeamList, TaskAuditLog
from .serializers import ProjectSerializer, TaskCommentSerializer, TaskSerializer, TaskAuditLogSerializer
from .services.permissions import (
    is_admin_user,
    user_can_access_project,
    user_is_project_manager,
    can_edit_task,
)
from .services.audit import log_task_action
from users.models import UserProfile
from users.models import TelegramLoginToken
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
import httpx

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
import logging

logger = logging.getLogger(__name__)

class TaskFrontendView(LoginRequiredMixin, TemplateView):
    """View для отображения основной страницы задач с Websocket и Vanilla JS."""
    template_name = 'tasks/index.html'


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Task.objects.filter(
            models.Q(assigned_to=user)
            | models.Q(created_by=user)
            | models.Q(list__members__user=user, list__members__is_active=True)
        ).select_related('list', 'assigned_to').distinct()

        status_param = self.request.query_params.get('status')
        list_param = self.request.query_params.get('list')
        assigned_param = self.request.query_params.get('assigned_to')
        q_param = self.request.query_params.get('q')
        ordering_param = self.request.query_params.get('ordering')

        if status_param:
            qs = qs.filter(status=status_param)
        if list_param:
            qs = qs.filter(list_id=list_param)
        if assigned_param:
            qs = qs.filter(assigned_to_id=assigned_param)
        if q_param:
            qs = qs.filter(Q(title__icontains=q_param) | Q(description__icontains=q_param))

        if ordering_param:
            allowed = {'due_date', '-due_date', 'updated_at', '-updated_at', 'priority', '-priority'}
            if ordering_param in allowed:
                qs = qs.order_by(ordering_param)

        return qs

    def perform_create(self, serializer):
        project = serializer.validated_data.get('list')
        if project and not user_can_access_project(self.request.user, project):
            raise PermissionDenied("You do not have permission to create tasks in this project.")
        task = serializer.save(created_by=self.request.user)
        log_task_action(task, self.request.user, TaskAuditLog.Action.CREATED, {
            'assigned_to_id': task.assigned_to_id,
            'list_id': task.list_id,
        })

    def perform_update(self, serializer):
        task = self.get_object()
        if not can_edit_task(self.request.user, task):
            raise PermissionDenied("You do not have permission to edit this task.")
        new_project = serializer.validated_data.get('list')
        if new_project and not user_can_access_project(self.request.user, new_project):
            raise PermissionDenied("You do not have permission to move tasks to this project.")
        task = serializer.save()
        log_task_action(task, self.request.user, TaskAuditLog.Action.UPDATED)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = get_object_or_404(Task, pk=pk)
        if not can_edit_task(request.user, task):
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)
        
        task.is_completed = True
        task.save(update_fields=['is_completed']) 
        log_task_action(task, request.user, TaskAuditLog.Action.COMPLETED)
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def uncomplete(self, request, pk=None):
        task = get_object_or_404(Task, pk=pk)
        if not can_edit_task(request.user, task):
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

        task.is_completed = False
        task.save(update_fields=['is_completed'])
        log_task_action(task, request.user, TaskAuditLog.Action.UNCOMPLETED)
        return Response(TaskSerializer(task).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def audit(self, request, pk=None):
        task = get_object_or_404(Task, pk=pk)
        if not user_can_access_project(request.user, task.list):
            return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)
        logs = task.audit_logs.select_related('actor').all()[:200]
        return Response(TaskAuditLogSerializer(logs, many=True).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        user = request.user
        qs = Task.objects.filter(
            models.Q(assigned_to=user)
            | models.Q(created_by=user)
            | models.Q(list__members__user=user, list__members__is_active=True)
        ).distinct()

        by_status = qs.values('status').annotate(count=models.Count('id'))
        return Response({
            'total': qs.count(),
            'by_status': list(by_status),
        }, status=status.HTTP_200_OK)
    
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

            # Не даём сохранить токен, если Telegram ещё не привязан.
            if not user_profile.telegram_chat_id:
                return Response({
                    "error": "Telegram account is not linked",
                    "detail": "Сначала привяжите Telegram (через /start <токен> в системном боте).",
                }, status=status.HTTP_400_BAD_REQUEST)

            # Валидация токена через Telegram API, чтобы не было ситуации "личный бот сохранён, но не работает".
            try:
                r = httpx.get(
                    f"https://api.telegram.org/bot{token}/getMe",
                    timeout=5,
                )
                data = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
                if r.status_code != 200 or not data.get('ok'):
                    return Response({
                        "error": "Invalid bot token",
                        "detail": "Telegram вернул ошибку. Проверьте токен BotFather.",
                    }, status=status.HTTP_400_BAD_REQUEST)
                if not username:
                    bot_username = (data.get('result') or {}).get('username')
                    if bot_username:
                        username = f"@{bot_username}"
            except Exception:
                return Response({
                    "error": "Token validation failed",
                    "detail": "Не удалось проверить токен. Попробуйте позже.",
                }, status=status.HTTP_400_BAD_REQUEST)
            
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
                        logger.info("Auto-linked chat_id %s to personal bot", user_profile.telegram_chat_id)
                except Exception as e:
                    logger.error("Error auto-linking chat_id: %s", e)
            
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
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'bot'

    def _get_profile(self, chat_id: str) -> UserProfile | None:
        if not chat_id:
            return None
        try:
            return UserProfile.objects.select_related('user').get(telegram_chat_id=str(chat_id))
        except UserProfile.DoesNotExist:
            return None

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """Информация о пользователе для Telegram (роль/привязка)."""
        chat_id = request.query_params.get('chat_id')
        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"linked": False}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "linked": True,
            "username": profile.user.username,
            "is_admin": is_admin_user(profile.user),
        })

    @action(detail=False, methods=['post'], url_path='web-login-token')
    def web_login_token(self, request):
        """Выдать одноразовую ссылку входа в веб по chat_id (для команды /login в Telegram)."""
        chat_id = request.data.get('chat_id')
        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)

        ttl = getattr(settings, 'TELEGRAM_LOGIN_TOKEN_TTL_SECONDS', 300)
        token = TelegramLoginToken.issue_for_user(profile.user, ttl_seconds=ttl)
        base = getattr(settings, 'WEB_BASE_URL', 'http://localhost:8005').rstrip('/')
        login_url = f"{base}/accounts/tg-login/{token.token}/"

        return Response({
            "status": "ok",
            "login_url": login_url,
            "expires_in": int(ttl),
        })

    @action(detail=False, methods=['post'], url_path='clear-personal-bot')
    def clear_personal_bot(self, request):
        """Отключить личного бота по chat_id (удаляет token/username в профиле)."""
        chat_id = request.data.get('chat_id')
        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)

        profile.personal_bot_token = None
        profile.personal_bot_username = None
        profile.save(update_fields=['personal_bot_token', 'personal_bot_username'])
        return Response({"status": "ok"})
    
    @action(detail=False, methods=['get'], url_path='get_user_tasks')
    def get_user_tasks(self, request):
        chat_id = request.query_params.get('chat_id')
        try:
            cache_key = f"bot_tasks:{chat_id}"
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

            profile = UserProfile.objects.get(telegram_chat_id=chat_id)
        
            tasks = Task.objects.filter(
                models.Q(assigned_to=profile.user) | models.Q(created_by=profile.user),
                is_completed=False
            ).select_related('list', 'assigned_to')
        
            serializer = TaskSerializer(tasks, many=True)
            cache.set(cache_key, serializer.data, timeout=15)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='projects')
    def projects(self, request):
        """Список доступных проектов (созданные или где пользователь участник)."""
        chat_id = request.query_params.get('chat_id')
        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)

        cache_key = f"bot_projects:{chat_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        user = profile.user
        qs = TeamList.objects.select_related('client', 'created_by').filter(
            Q(created_by=user) | Q(members__user=user, members__is_active=True)
        ).distinct().order_by('-updated_at')

        status_filter = request.query_params.get('status')
        q_param = request.query_params.get('q')
        ordering_param = request.query_params.get('ordering')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if q_param:
            qs = qs.filter(Q(name__icontains=q_param) | Q(description__icontains=q_param))
        if ordering_param:
            allowed = {'updated_at', '-updated_at', 'deadline', '-deadline'}
            if ordering_param in allowed:
                qs = qs.order_by(ordering_param)

        serializer = ProjectSerializer(qs, many=True)
        cache.set(cache_key, serializer.data, timeout=15)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='project')
    def project_detail(self, request):
        chat_id = request.query_params.get('chat_id')
        project_id = request.query_params.get('project_id')
        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)
        if not project_id:
            return Response({"error": "Missing project_id"}, status=status.HTTP_400_BAD_REQUEST)

        project = get_object_or_404(TeamList, pk=project_id)
        if not user_can_access_project(profile.user, project):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        serializer = ProjectSerializer(project)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='project-set-status')
    def project_set_status(self, request):
        chat_id = request.data.get('chat_id')
        project_id = request.data.get('project_id')
        new_status = request.data.get('status')

        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)
        if not project_id or not new_status:
            return Response({"error": "Missing project_id or status"}, status=status.HTTP_400_BAD_REQUEST)

        project = get_object_or_404(TeamList, pk=project_id)
        if not (user_is_project_manager(profile.user, project) or is_admin_user(profile.user)):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        allowed = {choice[0] for choice in TeamList.ProjectStatus.choices}
        if new_status not in allowed:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        project.status = new_status
        project.save(update_fields=['status', 'updated_at'])
        return Response({"status": "ok", "project_id": project.id, "project_status": project.status})

    @action(detail=False, methods=['get'], url_path='task')
    def task_detail(self, request):
        chat_id = request.query_params.get('chat_id')
        task_id = request.query_params.get('task_id')
        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)
        if not task_id:
            return Response({"error": "Missing task_id"}, status=status.HTTP_400_BAD_REQUEST)

        task = get_object_or_404(Task.objects.select_related('list', 'assigned_to', 'created_by'), pk=task_id)
        if not user_can_access_project(profile.user, task.list):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        task_data = TaskSerializer(task).data
        comments = TaskComment.objects.filter(task=task).select_related('author')[:20]
        comments_data = TaskCommentSerializer(comments, many=True).data
        return Response({"task": task_data, "comments": comments_data})

    @action(detail=False, methods=['post'], url_path='task-set-status')
    def task_set_status(self, request):
        chat_id = request.data.get('chat_id')
        task_id = request.data.get('task_id')
        new_status = request.data.get('status')

        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)
        if not task_id or not new_status:
            return Response({"error": "Missing task_id or status"}, status=status.HTTP_400_BAD_REQUEST)

        task = get_object_or_404(Task.objects.select_related('list'), pk=task_id)
        user = profile.user

        # Разрешаем менять статус: исполнитель, автор, менеджер проекта или админ
        if not (
            task.assigned_to_id == user.id
            or task.created_by_id == user.id
            or user_is_project_manager(user, task.list)
            or is_admin_user(user)
        ):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        allowed = {choice[0] for choice in Task.Status.choices}
        if new_status not in allowed:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        task.status = new_status
        task.save(update_fields=['status'])
        log_task_action(task, profile.user, TaskAuditLog.Action.STATUS_CHANGED, {
            'status': new_status,
        })
        return Response({"status": "ok", "task_id": task.id, "task_status": task.status})

    @action(detail=False, methods=['post'], url_path='task-comment')
    def task_comment(self, request):
        chat_id = request.data.get('chat_id')
        task_id = request.data.get('task_id')
        text = request.data.get('text')

        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)
        if not task_id or not text:
            return Response({"error": "Missing task_id or text"}, status=status.HTTP_400_BAD_REQUEST)

        task = get_object_or_404(Task.objects.select_related('list'), pk=task_id)
        if not user_can_access_project(profile.user, task.list):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        comment = TaskComment.objects.create(task=task, author=profile.user, text=str(text))
        log_task_action(task, profile.user, TaskAuditLog.Action.COMMENTED, {
            'comment_id': comment.id,
        })
        return Response({"status": "ok", "comment": TaskCommentSerializer(comment).data})

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Статистика задач для Telegram по chat_id."""
        chat_id = request.query_params.get('chat_id')
        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)

        user = profile.user
        qs = Task.objects.filter(
            Q(assigned_to=user) | Q(created_by=user)
        ).distinct()
        by_status = qs.values('status').annotate(count=models.Count('id'))
        return Response({
            'total': qs.count(),
            'by_status': list(by_status),
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='today')
    def today(self, request):
        """Задачи на сегодня (по due_date)."""
        chat_id = request.query_params.get('chat_id')
        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)

        user = profile.user
        day = timezone.localdate()
        start = timezone.make_aware(datetime.combine(day, time.min))
        end = timezone.make_aware(datetime.combine(day, time.max))

        tasks = Task.objects.filter(
            Q(assigned_to=user) | Q(created_by=user),
            is_completed=False,
            due_date__range=(start, end),
        ).select_related('list', 'assigned_to')

        return Response(TaskSerializer(tasks, many=True).data)

    @action(detail=False, methods=['post'], url_path='admin-create-project')
    def admin_create_project(self, request):
        """Создать проект из Telegram (только админ)."""
        chat_id = request.data.get('chat_id')
        name = request.data.get('name')
        description = request.data.get('description')
        source = request.data.get('source')
        client_name = request.data.get('client_name')

        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)
        if not is_admin_user(profile.user):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        if not name:
            return Response({"error": "Missing name"}, status=status.HTTP_400_BAD_REQUEST)

        client = None
        if client_name:
            client, _ = Client.objects.get_or_create(name=str(client_name), defaults={"created_by": profile.user})

        project = TeamList.objects.create(
            name=str(name),
            description=description,
            source=source,
            client=client,
            created_by=profile.user,
        )
        ProjectMember.objects.get_or_create(
            project=project,
            user=profile.user,
            defaults={"role": ProjectMember.Role.MANAGER},
        )
        return Response({"status": "ok", "project": ProjectSerializer(project).data})

    @action(detail=False, methods=['post'], url_path='admin-create-task')
    def admin_create_task(self, request):
        """Создать задачу в проекте (админ или менеджер проекта)."""
        chat_id = request.data.get('chat_id')
        project_id = request.data.get('project_id')
        title = request.data.get('title')
        description = request.data.get('description')
        assigned_to_username = request.data.get('assigned_to_username')

        profile = self._get_profile(chat_id)
        if not profile:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)
        if not project_id or not title:
            return Response({"error": "Missing project_id or title"}, status=status.HTTP_400_BAD_REQUEST)

        project = get_object_or_404(TeamList, pk=project_id)
        if not (is_admin_user(profile.user) or user_is_project_manager(profile.user, project)):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        assigned_to = None
        if assigned_to_username:
            User = get_user_model()
            try:
                assigned_to = User.objects.get(username=str(assigned_to_username))
            except User.DoesNotExist:
                return Response({"error": "Assigned user not found"}, status=status.HTTP_404_NOT_FOUND)

        task = Task.objects.create(
            title=str(title),
            description=description,
            list=project,
            assigned_to=assigned_to,
            created_by=profile.user,
        )
        log_task_action(task, profile.user, TaskAuditLog.Action.CREATED, {
            'assigned_to_id': task.assigned_to_id,
            'list_id': task.list_id,
        })
        return Response({"status": "ok", "task": TaskSerializer(task).data})

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
    
    @action(detail=False, methods=['post'], url_path='complete_task')
    def complete_task(self, request):
        """Завершить задачу по chat_id и task_id"""
        chat_id = request.data.get('chat_id')
        task_id = request.data.get('task_id')
        
        if not chat_id or not task_id:
            return Response({"error": "Missing chat_id or task_id"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            profile = UserProfile.objects.get(telegram_chat_id=chat_id)
            task = Task.objects.get(pk=task_id)
            
            # Проверяем права
            if task.assigned_to != profile.user and task.created_by != profile.user:
                return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
            
            task.is_completed = True
            task.save(update_fields=['is_completed'])
            self._log_task_action(task, profile.user, TaskAuditLog.Action.COMPLETED)
            
            return Response({"status": "Task completed"}, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response({"error": "User not linked"}, status=status.HTTP_404_NOT_FOUND)
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)
