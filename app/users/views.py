# app/users/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
# Импортируем нашу новую кастомную форму
from .forms import CustomUserCreationForm # <--- ИЗМЕНЕНИЕ

def register(request):
    """Обрабатывает форму регистрации, используя кастомную форму."""
    if request.method == 'POST':
        # Используем CustomUserCreationForm
        form = CustomUserCreationForm(request.POST) 
        if form.is_valid():
            form.save() 
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт создан для {username}! Теперь вы можете войти.')
            return redirect('users:login') # Используйте namespace
    else:
        form = CustomUserCreationForm() # <--- ИЗМЕНЕНИЕ
        
    return render(request, 'users/register.html', {'form': form})