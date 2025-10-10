# app/tasks/admin.py
from django.contrib import admin
from .models import Task, TeamList 

# Регистрация модели TeamList (КОРРЕКТНЫЕ ПОЛЯ)
@admin.register(TeamList)
class TeamListAdmin(admin.ModelAdmin):
    # Используем 'name' и 'created_by'
    list_display = ('name', 'created_by') 
    search_fields = ('name',)
    
# Регистрация модели Task
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    # Добавляем поле 'list' в list_display для удобства
    list_display = ('title', 'list', 'assigned_to', 'due_date', 'is_completed')
    list_filter = ('is_completed', 'due_date', 'list')
    search_fields = ('title', 'description')
    
    # Поля, которые можно редактировать на странице списка
    list_editable = ('is_completed',) 
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description')
        }),
        ('Организация', {
            'fields': ('list',) # Добавляем TeamList
        }),
        ('Назначение', {
            'fields': ('assigned_to', 'created_by')
        }),
        ('Статус и Сроки', {
            'fields': ('due_date', 'is_completed')
            # Мы не добавляем 'telegram_notification_sent', так как оно отсутствует в модели Task.
        }),
    )
