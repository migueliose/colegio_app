import os
from decouple import config
from django.core.wsgi import get_wsgi_application

# Determinar entorno
environment = config('DJANGO_ENV', default='production')

if environment == 'production':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colegio_app.settings.prod')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colegio_app.settings.dev')

application = get_wsgi_application()