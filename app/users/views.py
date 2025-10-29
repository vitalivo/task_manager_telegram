# app/users/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import CustomUserCreationForm
from .models import UserProfile

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