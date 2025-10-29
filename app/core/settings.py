import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta
import dj_database_url 
from urllib.parse import urlparse

# Load environment variables from .env file for local development
load_dotenv() 

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- CORE SETTINGS ---
SECRET_KEY = os.environ.get('SECRET_KEY', 'default-insecure-key')
# Default to False for security in deployment, override with DEBUG=True only locally
# Важно: для локального тестирования в .env должен быть DEBUG=True
DEBUG = os.environ.get('DEBUG', 'False') == 'True' 

# --- HOST AND SECURITY CONFIGURATION (FIXED) ---
# Your actual domain from Render logs
DEPLOYMENT_HOST = 'task-manager-telegram.onrender.com'
# RENDER provides this variable, essential for ALLOWED_HOSTS
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')

# Build ALLOWED_HOSTS list
ALLOWED_HOSTS = ['localhost', 'app', '127.0.0.1',  '0.0.0.0', DEPLOYMENT_HOST]

if RENDER_EXTERNAL_HOSTNAME:
    # Add the RENDER provided hostname
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

ALLOWED_HOSTS = list(set(ALLOWED_HOSTS)) # Remove duplicates

# CSRF Trusted Origins - Essential for deployment
CSRF_TRUSTED_ORIGINS = [f'https://{DEPLOYMENT_HOST}']
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')
# Add local trusted origins
CSRF_TRUSTED_ORIGINS.extend([
    'http://localhost:8005',
    'http://127.0.0.1:8005',
])


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'channels',
    'django_celery_beat',
    'crispy_forms',
    'corsheaders',
    # Local apps
    'users',
    'tasks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# --- DATABASE CONFIGURATION (FIXED) ---
DATABASES = {
    'default': dj_database_url.config(
        # Use DATABASE_URL from environment, fall back to SQLite for robust local dev
        default='sqlite:///db.sqlite3',
        conn_max_age=600,
        # Удалили: conn_health_check=True,
    )
}

# --- REDIS/CHANNELS/CELERY CONFIGURATION (FIXED for Local/Render) ---

# REDIS_URL from Render env variable (used in production/DEBUG=False)
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

if DEBUG:
    # Local development (Docker Compose) - use container name 'redis'
    CHANNELS_HOSTS = [('redis', 6379)]
    BROKER_URL = 'redis://redis:6379/0'
else:
    # Production (Render) - use REDIS_URL variable
    CHANNELS_HOSTS = [REDIS_URL]
    BROKER_URL = REDIS_URL

# Channels (Websockets)
ASGI_APPLICATION = 'core.asgi.application'
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],  # всегда используем REDIS_URL
        },
    },
}

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
# Celery Beat
CELERY_BEAT_SCHEDULE = {
    'check-deadlines-every-5-minutes': {
        'task': 'tasks.tasks.check_deadlines', # Путь к задаче
        'schedule': timedelta(minutes=5),
    },
}

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Rest Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication', 
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}
# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

TIME_ZONE = 'Europe/Moscow'
# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    # Remove this line if you put static files inside app/static/
    # BASE_DIR / 'static', 
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# This is often redundant if CSRF_TRUSTED_ORIGINS is set correctly, 
# but useful for completeness if using local CORS requests.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4" 
CRISPY_TEMPLATE_PACK = "bootstrap4"