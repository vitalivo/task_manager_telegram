from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
# Сигнал для автоматического создания UserProfile
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    # Кастомная модель пользователя, можно расширять
    pass

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telegram_chat_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name=_('Telegram chat_id'),
    )
    verification_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    personal_bot_token = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name=_('Токен личного бота')
    )
    personal_bot_username = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name=_('Username личного бота')
    )
    
    # --- ДОБАВЛЕНИЕ РУССКИХ НАЗВАНИЙ ДЛЯ АДМИНКИ ---
    class Meta:
        verbose_name = _('Профиль пользователя')
        verbose_name_plural = _('Профили пользователей')
    # --------------------------------------------------

    def __str__(self):
        return f"Профиль: {self.user.username}"


class TelegramLoginToken(models.Model):
    """Одноразовый токен для быстрого входа в веб через Telegram."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='telegram_login_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = _('Токен входа Telegram')
        verbose_name_plural = _('Токены входа Telegram')
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['expires_at']),
        ]

    @classmethod
    def issue_for_user(cls, user: User, ttl_seconds: int = 300) -> 'TelegramLoginToken':
        now = timezone.now()
        return cls.objects.create(
            user=user,
            expires_at=now + timedelta(seconds=int(ttl_seconds)),
        )

    def is_valid(self) -> bool:
        if self.used_at is not None:
            return False
        return timezone.now() <= self.expires_at

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
