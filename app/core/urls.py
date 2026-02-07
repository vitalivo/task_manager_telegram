"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# app/core/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tasks.views import TaskViewSet, TaskBotAPIView 
from django.conf import settings # <--- ИМПОРТ
from django.conf.urls.static import static # <--- ИМПОРТ
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from .views import healthcheck

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'bot/tasks', TaskBotAPIView, basename='bot-task')

admin.site.site_header = 'Панель управления'
admin.site.site_title = 'TaskFlow Админ'
admin.site.index_title = 'Администрирование'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', healthcheck, name='healthcheck'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')), 
    path('accounts/', include('django.contrib.auth.urls')),
    
    # НОВОЕ: Подключаем URLs для аутентификации
    path('accounts/', include('users.urls')), 
    
    path('', include('tasks.urls')), 
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Если вы используете медиафайлы, добавьте:
    # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)