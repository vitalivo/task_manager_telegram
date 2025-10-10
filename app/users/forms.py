# app/users/forms.py

from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User  # Импортируйте вашу кастомную модель User

# Форма для регистрации (замена стандартной UserCreationForm)
class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        # Явно указываем, что это форма для вашей модели users.User
        model = User
        # Включаем все нужные поля (обычно username и email, если есть)
        fields = ('username',) # Оставьте только те поля, которые нужны для создания
        # fields = UserCreationForm.Meta.fields + ('email',) # Пример добавления email