from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from users.models import User


class Client(models.Model):
    name = models.CharField(max_length=255, verbose_name=_('Клиент / Компания'))
    contact_person = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Контактное лицо'))
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name=_('Телефон'))
    email = models.EmailField(blank=True, null=True, verbose_name=_('Email'))
    telegram = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Telegram'))
    notes = models.TextField(blank=True, null=True, verbose_name=_('Заметки'))

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients_created',
        verbose_name=_('Создатель'),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлено'))

    class Meta:
        verbose_name = _('Клиент')
        verbose_name_plural = _('Клиенты')
        ordering = ('name',)

    def __str__(self):
        return self.name

class TeamList(models.Model):
    class ProjectStatus(models.TextChoices):
        NEGOTIATION = 'negotiation', _('Переписка')
        DEVELOPMENT = 'development', _('В разработке')
        REJECTED = 'rejected', _('Не принят')
        DONE = 'done', _('Завершён')

    class ProjectSource(models.TextChoices):
        TELEGRAM = 'telegram', _('Telegram')
        WEBSITE = 'website', _('Сайт')
        RECOMMENDATION = 'recommendation', _('Рекомендация')
        RETURNING = 'returning', _('Повторный клиент')
        OTHER = 'other', _('Другое')

    name = models.CharField(max_length=100, verbose_name=_('Название'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Описание / ТЗ'))

    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='projects',
        verbose_name=_('Клиент'),
    )

    status = models.CharField(
        max_length=32,
        choices=ProjectStatus.choices,
        default=ProjectStatus.NEGOTIATION,
        verbose_name=_('Статус'),
    )
    source = models.CharField(
        max_length=32,
        choices=ProjectSource.choices,
        blank=True,
        null=True,
        verbose_name=_('Источник'),
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name=_('Цена'),
        help_text=_('Общая стоимость проекта (позже добавим финансы детальнее).'),
    )
    start_date = models.DateField(blank=True, null=True, verbose_name=_('Дата старта'))
    deadline = models.DateField(blank=True, null=True, verbose_name=_('Срок (дедлайн)'))
    rejected_reason = models.TextField(blank=True, null=True, verbose_name=_('Причина отказа'))

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='task_lists',
        verbose_name=_('Создатель'),
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        verbose_name=_('Создано'),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Обновлено'),
    )

    class Meta:
        verbose_name = _('Проект')
        verbose_name_plural = _('Проекты')
        ordering = ('-updated_at',)
    def __str__(self):
        return f"{self.name}"


class ProjectMember(models.Model):
    class Role(models.TextChoices):
        MANAGER = 'manager', _('Менеджер')
        EXECUTOR = 'executor', _('Исполнитель')
        VIEWER = 'viewer', _('Наблюдатель')

    project = models.ForeignKey(
        TeamList,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name=_('Проект'),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='project_memberships',
        verbose_name=_('Пользователь'),
    )
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.EXECUTOR, verbose_name=_('Роль'))
    is_active = models.BooleanField(default=True, verbose_name=_('Активен'))
    added_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Добавлен'))

    class Meta:
        verbose_name = _('Участник проекта')
        verbose_name_plural = _('Участники проекта')
        constraints = [
            models.UniqueConstraint(fields=['project', 'user'], name='unique_project_member')
        ]

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


class ConversationMessage(models.Model):
    class Kind(models.TextChoices):
        INTERNAL = 'internal', _('Внутренняя заметка')
        CLIENT = 'client', _('Сообщение клиенту')

    project = models.ForeignKey(
        TeamList,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Проект'),
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_messages',
        verbose_name=_('Автор'),
    )
    kind = models.CharField(max_length=32, choices=Kind.choices, default=Kind.INTERNAL, verbose_name=_('Тип'))
    text = models.TextField(verbose_name=_('Текст'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))

    class Meta:
        verbose_name = _('Сообщение')
        verbose_name_plural = _('Сообщения')
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.project.name}: {self.text[:50]}"

class Task(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', _('Новая')
        IN_PROGRESS = 'in_progress', _('В работе')
        REVIEW = 'review', _('На проверке')
        DONE = 'done', _('Готово')

    class Priority(models.TextChoices):
        LOW = 'low', _('Низкий')
        MEDIUM = 'medium', _('Средний')
        HIGH = 'high', _('Высокий')
        CRITICAL = 'critical', _('Критичный')

    title = models.CharField(max_length=255, verbose_name=_('Название'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Описание'))
    list = models.ForeignKey(TeamList, on_delete=models.CASCADE, related_name='tasks', verbose_name=_('Проект'))
    
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tasks_assigned',
        verbose_name=_('Исполнитель'),
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tasks_created',
        verbose_name=_('Автор'),
    )
    
    due_date = models.DateTimeField(null=True, blank=True, verbose_name=_('Срок'))
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name=_('Статус'),
    )
    priority = models.CharField(
        max_length=16,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name=_('Приоритет'),
    )
    is_completed = models.BooleanField(default=False, verbose_name=_('Выполнено'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Обновлено'))
    started_at = models.DateTimeField(blank=True, null=True, verbose_name=_('Начато'))
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name=_('Завершено'))
    estimate_hours = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name=_('Оценка, ч'))
    actual_hours = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, verbose_name=_('Факт, ч'))

    class Meta:
        ordering = ['due_date', '-created_at']
        verbose_name = _('Задача')
        verbose_name_plural = _('Задачи')
        indexes = [
            models.Index(fields=['status'], name='task_status_idx'),
            models.Index(fields=['due_date'], name='task_due_date_idx'),
            models.Index(fields=['assigned_to'], name='task_assigned_idx'),
            models.Index(fields=['list'], name='task_list_idx'),
        ]

    def __str__(self):
        return f"{self.title}"

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        changed_fields = set(update_fields) if update_fields is not None else None

        # Двусторонняя синхронизация: статус <-> is_completed
        status_changed = changed_fields is not None and 'status' in changed_fields
        completed_changed = changed_fields is not None and 'is_completed' in changed_fields

        if status_changed:
            if self.status == self.Status.DONE:
                self.is_completed = True
                if changed_fields is not None:
                    changed_fields.add('is_completed')
                if self.completed_at is None:
                    self.completed_at = timezone.now()
                    if changed_fields is not None:
                        changed_fields.add('completed_at')
            else:
                self.is_completed = False
                if changed_fields is not None:
                    changed_fields.add('is_completed')
                if self.completed_at is not None:
                    self.completed_at = None
                    if changed_fields is not None:
                        changed_fields.add('completed_at')
        elif completed_changed:
            if self.is_completed:
                self.status = self.Status.DONE
                if changed_fields is not None:
                    changed_fields.add('status')
                if self.completed_at is None:
                    self.completed_at = timezone.now()
                    if changed_fields is not None:
                        changed_fields.add('completed_at')
            else:
                if self.status == self.Status.DONE:
                    self.status = self.Status.NEW
                    if changed_fields is not None:
                        changed_fields.add('status')
                if self.completed_at is not None:
                    self.completed_at = None
                    if changed_fields is not None:
                        changed_fields.add('completed_at')
        else:
            if self.status == self.Status.DONE:
                self.is_completed = True
                if changed_fields is not None:
                    changed_fields.add('is_completed')
                if self.completed_at is None:
                    self.completed_at = timezone.now()
                    if changed_fields is not None:
                        changed_fields.add('completed_at')
            else:
                self.is_completed = False
                if changed_fields is not None:
                    changed_fields.add('is_completed')
                if self.completed_at is not None:
                    self.completed_at = None
                    if changed_fields is not None:
                        changed_fields.add('completed_at')

        if self.status == self.Status.IN_PROGRESS and self.started_at is None:
            self.started_at = timezone.now()
            if changed_fields is not None:
                changed_fields.add('started_at')

        if changed_fields is not None:
            kwargs['update_fields'] = list(changed_fields)

        super().save(*args, **kwargs)


class TaskComment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments', verbose_name=_('Задача'))
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='task_comments',
        verbose_name=_('Автор'),
    )
    text = models.TextField(verbose_name=_('Комментарий'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))

    class Meta:
        verbose_name = _('Комментарий к задаче')
        verbose_name_plural = _('Комментарии к задачам')
        ordering = ('-created_at',)

    def __str__(self):
        return f"#{self.task_id}: {self.text[:40]}"


class TaskAuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = 'created', _('Создана')
        UPDATED = 'updated', _('Обновлена')
        STATUS_CHANGED = 'status_changed', _('Статус изменён')
        COMPLETED = 'completed', _('Завершена')
        UNCOMPLETED = 'uncompleted', _('Возвращена в работу')
        COMMENTED = 'commented', _('Комментарий')

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='audit_logs', verbose_name=_('Задача'))
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='task_audit_logs', verbose_name=_('Пользователь'))
    action = models.CharField(max_length=32, choices=Action.choices, verbose_name=_('Действие'))
    details = models.JSONField(blank=True, null=True, verbose_name=_('Детали'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Создано'))

    class Meta:
        verbose_name = _('Аудит задачи')
        verbose_name_plural = _('Аудит задач')
        ordering = ('-created_at',)

    def __str__(self):
        return f"{self.task_id}: {self.action}"
