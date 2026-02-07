from django.contrib import admin

from .models import Client, ConversationMessage, ProjectMember, Task, TaskComment, TeamList, TaskAuditLog

# --- Русификация django_celery_beat в админке (proxy модели, без миграций) ---
try:
    from django_celery_beat.admin import (
        PeriodicTaskAdmin,
        IntervalScheduleAdmin,
        CrontabScheduleAdmin,
        SolarScheduleAdmin,
        ClockedScheduleAdmin,
    )
    from django_celery_beat.models import (
        PeriodicTask,
        IntervalSchedule,
        CrontabSchedule,
        SolarSchedule,
        ClockedSchedule,
    )

    class PeriodicTaskRu(PeriodicTask):
        class Meta:
            proxy = True
            verbose_name = 'Периодическая задача'
            verbose_name_plural = 'Периодические задачи'

    class IntervalScheduleRu(IntervalSchedule):
        class Meta:
            proxy = True
            verbose_name = 'Интервал'
            verbose_name_plural = 'Интервалы'

    class CrontabScheduleRu(CrontabSchedule):
        class Meta:
            proxy = True
            verbose_name = 'Расписание (cron)'
            verbose_name_plural = 'Расписания (cron)'

    class SolarScheduleRu(SolarSchedule):
        class Meta:
            proxy = True
            verbose_name = 'Астрономическое событие'
            verbose_name_plural = 'Астрономические события'

    class ClockedScheduleRu(ClockedSchedule):
        class Meta:
            proxy = True
            verbose_name = 'Время'
            verbose_name_plural = 'Время'

    for model in (PeriodicTask, IntervalSchedule, CrontabSchedule, SolarSchedule, ClockedSchedule):
        try:
            admin.site.unregister(model)
        except admin.sites.NotRegistered:
            pass

    admin.site.register(PeriodicTaskRu, PeriodicTaskAdmin)
    admin.site.register(IntervalScheduleRu, IntervalScheduleAdmin)
    admin.site.register(CrontabScheduleRu, CrontabScheduleAdmin)
    admin.site.register(SolarScheduleRu, SolarScheduleAdmin)
    admin.site.register(ClockedScheduleRu, ClockedScheduleAdmin)
except Exception:
    # Если пакет django_celery_beat не установлен/не подключен, просто пропускаем.
    pass


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0
    autocomplete_fields = ('user',)


class ConversationMessageInline(admin.StackedInline):
    model = ConversationMessage
    extra = 0
    autocomplete_fields = ('author',)
    fields = ('kind', 'author', 'text', 'created_at')
    readonly_fields = ('created_at',)


class TaskCommentInline(admin.StackedInline):
    model = TaskComment
    extra = 0
    autocomplete_fields = ('author',)
    fields = ('author', 'text', 'created_at')
    readonly_fields = ('created_at',)


class TaskAuditLogInline(admin.TabularInline):
    model = TaskAuditLog
    extra = 0
    can_delete = False
    autocomplete_fields = ('actor',)
    fields = ('action', 'actor', 'created_at', 'details')
    readonly_fields = ('action', 'actor', 'created_at', 'details')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'telegram', 'updated_at')
    search_fields = ('name', 'contact_person', 'phone', 'email', 'telegram')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(TeamList)
class TeamListAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'source', 'price', 'deadline', 'created_by', 'updated_at')
    list_filter = ('status', 'source', 'deadline', 'created_by')
    search_fields = ('name', 'description', 'rejected_reason', 'created_by__username')
    list_editable = ('status',)
    ordering = ('-updated_at',)

    autocomplete_fields = ('client', 'created_by')
    inlines = (ProjectMemberInline, ConversationMessageInline)

    fieldsets = (
        ('Основное', {
            'fields': ('name', 'client', 'description')
        }),
        ('Статус', {
            'fields': ('status', 'source', 'rejected_reason')
        }),
        ('Сроки и стоимость', {
            'fields': ('price', 'start_date', 'deadline')
        }),
        ('Служебное', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'list', 'assigned_to', 'status', 'priority', 'due_date', 'is_completed', 'updated_at')
    list_filter = ('status', 'priority', 'is_completed', 'due_date', 'list', 'assigned_to')
    search_fields = ('title', 'description', 'list__name', 'assigned_to__username', 'created_by__username')
    
    list_editable = ('is_completed',) 
    
    autocomplete_fields = ('list', 'assigned_to', 'created_by')
    inlines = (TaskCommentInline, TaskAuditLogInline)

    fieldsets = (
        (None, {
            'fields': ('title', 'description')
        }),
        ('Проект', {
            'fields': ('list',)
        }),
        ('Назначение', {
            'fields': ('assigned_to', 'created_by')
        }),
        ('Статус и Сроки', {
            'fields': ('status', 'priority', 'due_date', 'is_completed')
        }),
        ('План/факт', {
            'fields': ('estimate_hours', 'actual_hours', 'started_at', 'completed_at')
        }),
    )

    readonly_fields = ('created_at', 'updated_at', 'started_at', 'completed_at')


@admin.register(TaskAuditLog)
class TaskAuditLogAdmin(admin.ModelAdmin):
    list_display = ('task', 'action', 'actor', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('task__title', 'actor__username')
    readonly_fields = ('task', 'action', 'actor', 'details', 'created_at')
