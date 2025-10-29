# app/users/admin.py
from django.contrib import admin
from .models import User, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'telegram_chat_id', 'personal_bot_username', 'verification_token')
    search_fields = ('user__username', 'telegram_chat_id', 'personal_bot_username', 'verification_token')
    readonly_fields = ('verification_token',)  # ИСПРАВЛЕННАЯ строка
