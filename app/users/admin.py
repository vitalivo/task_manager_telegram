# app/users/admin.py
from django.contrib import admin
from .models import User, UserProfile

# Регистрация модели UserProfile
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'telegram_chat_id', 'verification_token')
    search_fields = ('user__username', 'telegram_chat_id', 'verification_token')
    # Поля, которые можно изменять
    readonly_fields = ('verification_token',)
