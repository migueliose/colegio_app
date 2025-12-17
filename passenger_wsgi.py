import sys
import os

# Ruta base del proyecto
PROJECT_PATH = '/home/colegioc/public_html/colegio'

# Agregar el proyecto al path
if PROJECT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_PATH)

# Variable de entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'colegio_app.settings')

# Activar entorno virtual (IMPORTANTE)
activate_env = '/home/colegioc/virtualenv/public_html/colegio/3.12/bin/activate_this.py'
with open(activate_env) as f:
    exec(f.read(), {'__file__': activate_env})

# WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
