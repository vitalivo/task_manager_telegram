# app/users/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings
from .forms import CustomUserCreationForm
from .models import UserProfile, TelegramLoginToken

def register(request):
    """Обрабатывает форму регистрации, используя кастомную форму."""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            
            # АВТОМАТИЧЕСКАЯ ПРИВЯЗКА: Ищем существующий chat_id по email
            email = form.cleaned_data.get('email')
            if email:
                try:
                    # Ищем пользователей с таким же email которые уже привязали Telegram
                    existing_profiles = UserProfile.objects.filter(
                        user__email=email,
                        telegram_chat_id__isnull=False
                    )
                    if existing_profiles.exists():
                        # Берем первый найденный chat_id
                        existing_chat_id = existing_profiles.first().telegram_chat_id
                        user.profile.telegram_chat_id = existing_chat_id
                        user.profile.save()
                        messages.success(request, f'Аккаунт создан для {username}! Telegram автоматически привязан.')
                    else:
                        messages.success(request, f'Аккаунт создан для {username}! Теперь вы можете войти.')
                except Exception as e:
                    messages.success(request, f'Аккаунт создан для {username}! Теперь вы можете войти.')
            else:
                messages.success(request, f'Аккаунт создан для {username}! Теперь вы можете войти.')
                
            return redirect('users:login')
    else:
        form = CustomUserCreationForm()
        
    return render(request, 'users/register.html', {'form': form})


def telegram_login(request, token):
    """Быстрый вход в веб по одноразовой ссылке из Telegram."""
    try:
        login_token = TelegramLoginToken.objects.select_related('user').get(token=token)
    except TelegramLoginToken.DoesNotExist:
        messages.error(request, 'Ссылка входа недействительна или устарела.')
        return render(request, 'users/tg_login_error.html', status=400)

    if not login_token.is_valid():
        messages.error(request, 'Ссылка входа недействительна или устарела.')
        return render(request, 'users/tg_login_error.html', status=400)

    login_token.used_at = timezone.now()
    login_token.save(update_fields=['used_at'])

    login(request, login_token.user)

    next_url = request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)

    return redirect(settings.LOGIN_REDIRECT_URL or '/')