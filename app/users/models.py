from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
# Сигнал для автоматического создания UserProfile
from django.db.models.signals import post_save
from django.dispatch import receiver

class User(AbstractUser):
    # Кастомная модель пользователя, можно расширять
    pass

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name='Telegram Chat ID')
    verification_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # --- ДОБАВЛЕНИЕ РУССКИХ НАЗВАНИЙ ДЛЯ АДМИНКИ ---
    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"
    # --------------------------------------------------

    def __str__(self):
        # Обновляем, чтобы в списке было 'Профиль admin123' вместо 'Profile of admin123'
        return f"Профиль {self.user.username}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
