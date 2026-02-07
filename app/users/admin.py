from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User, UserProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'telegram_chat_id', 'personal_bot_username', 'verification_token')
    search_fields = ('user__username', 'telegram_chat_id', 'personal_bot_username', 'verification_token')
    readonly_fields = ('verification_token',)  # ИСПРАВЛЕННАЯ строка
