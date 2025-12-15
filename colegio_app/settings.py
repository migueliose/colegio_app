"""
Django settings for colegio_app project.
Producción – Colegio Cristiano El Shadai
"""

from pathlib import Path
import os
from decouple import config, Csv

# ===============================
# BASE
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent

# ===============================
# SECURITY
# ===============================
SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', cast=bool)
# ======================
# SEGURIDAD PRODUCCIÓN
# ======================
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = True 
#======================
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    cast=Csv()
)

CSRF_TRUSTED_ORIGINS = [
    'https://colegiocrishadai.edu.co',
    'https://www.colegiocrishadai.edu.co',
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
X_FRAME_OPTIONS = 'DENY'

# ===============================
# APPLICATIONS
# ===============================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceros
    'widget_tweaks',
    'crispy_forms',
    'crispy_bootstrap5',

    # Apps del proyecto
    'web',
    'gestioncolegio',
    'usuarios',
    'academico',
    'matricula',
    'estudiantes',
    'comportamiento',
    'acudiente',
    'docentes',
    'administrador',
]

AUTH_USER_MODEL = 'usuarios.Usuario'

# ===============================
# MIDDLEWARE
# ===============================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# ===============================
# URLS / WSGI
# ===============================
ROOT_URLCONF = 'colegio_app.urls'
WSGI_APPLICATION = 'colegio_app.wsgi.application'

# ===============================
# TEMPLATES
# ===============================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                # Context processors personalizados
                'web.context_processors.programas_context',
                'gestioncolegio.context_processors.informacion_colegio',
                'gestioncolegio.context_processors.menu_sistema',
                'gestioncolegio.context_processors.periodo_actual_processor',
                'gestioncolegio.context_processors.acudiente_menu',
                'gestioncolegio.context_processors.año_lectivo_admin_context',
            ],
        },
    },
]

# ===============================
# DATABASES
# ===============================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DATABASE_NAME'),
        'USER': config('DATABASE_USER'),
        'PASSWORD': config('DATABASE_PASSWORD'),
        'HOST': config('DATABASE_HOST'),
        'PORT': config('DATABASE_PORT'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    },
    'antigua': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DATABASE_NAME_ANT'),
        'USER': config('DATABASE_USER'),
        'PASSWORD': config('DATABASE_PASSWORD'),
        'HOST': config('DATABASE_HOST'),
        'PORT': config('DATABASE_PORT'),
    }
}

DATABASE_ROUTERS = ['colegio_app.routers.AntiguaDBRouter']

# ===============================
# AUTH PASSWORD VALIDATORS
# ===============================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ===============================
# INTERNATIONALIZATION
# ===============================
LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# ===============================
# STATIC & MEDIA
# ===============================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ===============================
# AUTH REDIRECTS
# ===============================
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'web:perfil'
LOGOUT_REDIRECT_URL = 'web:home'

# ===============================
# EMAIL
# ===============================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ===============================
# CRISPY FORMS
# ===============================
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ===============================
# DEFAULT FIELD
# ===============================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
